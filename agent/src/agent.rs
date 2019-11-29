use std::collections::hash_map::DefaultHasher;
use std::fs::{remove_file, File, Permissions};
use std::hash::{Hash, Hasher};
use std::io::{BufRead, BufReader, BufWriter, Error, ErrorKind, Read, Result, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::process::ExitStatusExt;
use std::mem::drop;
use std::process::{id as get_pid, Command, ExitStatus, Stdio};
use std::sync::mpsc::channel;
use std::thread::{current as current_thread, spawn};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use wait_timeout::ChildExt;

use crate::config::Config;
use crate::models::{
    Compilation, CompilationResult, ErrorResult, Preparation, Request, Response, TestRequest,
    TestResult,
};

pub struct Agent<R: Read, W: Write> {
    config: Config,
    reader: BufReader<R>,
    writer: BufWriter<W>,
    buf: Vec<u8>,

    time_limit: u32,
    memory_limit: u32,
    output_limit: u32,
}

impl<R: Read, W: Write> Agent<R, W> {
    pub fn new(mut config: Config, reader: R, writer: W) -> Self {
        let temp_prefix = format!(
            "/tmp/penguin_judge_tempfile_{}_{}_{}",
            {
                let e = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
                format!("{}{:09}", e.as_secs(), e.subsec_nanos())
            },
            get_pid(),
            {
                let mut hasher = DefaultHasher::new();
                current_thread().id().hash(&mut hasher);
                hasher.finish()
            }
        );

        fn replace_keyword(
            temp_prefix: &str,
            path: &mut String,
            ext: &str,
            output: Option<&mut String>,
            args: &mut Vec<String>,
        ) {
            if path.is_empty() {
                path.push_str(&format!("{}{}", temp_prefix, ext));
            }
            let out = match output {
                Some(s) => {
                    if s.is_empty() {
                        s.push_str(temp_prefix);
                    }
                    s.to_string()
                }
                _ => "".to_string(),
            };
            for arg in args {
                if arg == "<path>" {
                    *arg = path.clone();
                } else if arg == "<output>" {
                    *arg = out.clone();
                }
            }
        }

        if let Some(ccfg) = &mut config.compile.as_mut() {
            replace_keyword(
                &temp_prefix,
                &mut ccfg.path,
                &ccfg.ext,
                Some(&mut ccfg.output),
                &mut ccfg.args,
            );
        }
        if let Some(tcfg) = &mut config.test.as_mut() {
            replace_keyword(
                &temp_prefix,
                &mut tcfg.path,
                &tcfg.ext,
                None,
                &mut tcfg.args,
            );
            if tcfg.cmd.is_empty() {
                tcfg.cmd = tcfg.path.clone();
            }
        }
        Agent {
            config,
            reader: BufReader::new(reader),
            writer: BufWriter::new(writer),
            buf: Vec::new(),
            time_limit: 0,
            memory_limit: 0,
            output_limit: 0,
        }
    }

    pub fn start(&mut self) -> Result<()> {
        match self.recv()? {
            Request::Compilation(c) => {
                let resp = self.process_compile(c)?;
                return self.send(&resp);
            }
            Request::Preparation(p) => {
                self.process_prepare(p)?;
            }
            _ => return Err(Error::new(ErrorKind::InvalidInput, "Invalid First Message")),
        };
        loop {
            let req = match self.recv()? {
                Request::Fin => {
                    break;
                }
                Request::Test(r) => r,
                _ => return Err(Error::new(ErrorKind::InvalidInput, "TestRequest required")),
            };
            let res = self.process_test(req)?;
            self.send(&res)?;
        }
        Ok(())
    }

    fn process_compile(&mut self, req: Compilation) -> Result<Response> {
        let compile_cfg = self.config.compile.as_ref().unwrap();
        {
            let mut f = File::create(&compile_cfg.path)?;
            f.write_all(&req.code)?;
        }
        let timeout = Duration::from_secs(u64::from(req.time_limit));
        let mut cmd = Command::new(&compile_cfg.cmd);
        for arg in &compile_cfg.args {
            cmd.arg(arg);
        }
        let start_time = Instant::now();
        let mut child = cmd.stdout(Stdio::null()).stderr(Stdio::null()).spawn()?;
        match child.wait_timeout(timeout)? {
            Some(status) => {
                if status.success() {
                    let d = Instant::now().duration_since(start_time);
                    if let Ok(mut f) = File::open(&compile_cfg.output) {
                        let mut bin = Vec::new();
                        if f.read_to_end(&mut bin).is_ok() {
                            return Ok(Response::Compilation(CompilationResult {
                                binary: bin,
                                time: d.as_secs_f64(),
                                memory: 0,
                            }));
                        }
                    }
                }
                Ok(Response::Error {
                    kind: {
                        if is_oom(status) {
                            ErrorResult::MemoryLimitExceeded
                        } else {
                            ErrorResult::CompilationError
                        }
                    },
                })
            }
            None => {
                child.kill()?;
                child.wait()?;
                Ok(Response::Error {
                    kind: ErrorResult::TimeLimitExceeded,
                })
            }
        }
    }

    fn process_prepare(&mut self, config: Preparation) -> Result<()> {
        let test_cfg = self.config.test.as_ref().unwrap();
        self.time_limit = config.time_limit;
        self.memory_limit = config.memory_limit;
        self.output_limit = config.output_limit * 2u32.pow(20);
        let mut f = File::create(&test_cfg.path)?;
        f.set_permissions(Permissions::from_mode(0o755))?;
        f.write_all(&config.code)
    }

    fn process_test(&mut self, req: TestRequest) -> Result<Response> {
        let test_cfg = self.config.test.as_ref().unwrap();
        let timeout = Duration::from_secs(u64::from(self.time_limit));
        let mut cmd = Command::new(&test_cfg.cmd);
        for arg in &test_cfg.args {
            cmd.arg(arg);
        }
        let start_time = Instant::now();
        let deadline = start_time + timeout;
        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()?;
        let mut child_stdin = child.stdin.take().unwrap();
        let mut child_stdout = child.stdout.take().unwrap();
        let (sender, receiver) = channel();
        let procfs_path = format!("/proc/{}/status", child.id());
        #[derive(Debug)]
        enum Msg {
            Data(Vec<u8>),
            Fin(u64, bool), // VmHWM, OLE-flag
            Err,
        }
        let mut output: Vec<u8> = Vec::new();
        let output_limit = self.output_limit;
        let handler = spawn(move || {
            let get_hwm = |prev_value: u64| {
                std::cmp::max(prev_value, read_vm_hwm(&procfs_path).unwrap_or(prev_value))
            };
            let mut last_hwm = get_hwm(0u64);
            if child_stdin.write_all(&req.input).is_err() || child_stdin.flush().is_err() {
                return;
            }
            drop(child_stdin);
            let mut total_bytes: usize = 0;
            loop {
                let mut v: Vec<u8> = Vec::new();
                v.resize(1024, 0);
                last_hwm = get_hwm(last_hwm);
                let ret = child_stdout.read(v.as_mut_slice());
                last_hwm = get_hwm(last_hwm);
                let size = match ret {
                    Err(_) => {
                        sender.send(Msg::Err).unwrap();
                        return;
                    }
                    Ok(0) => {
                        sender.send(Msg::Fin(get_hwm(last_hwm), false)).unwrap();
                        return;
                    }
                    Ok(s) => s,
                };
                total_bytes += size;
                if total_bytes >= output_limit as usize {
                    sender.send(Msg::Fin(get_hwm(last_hwm), true)).unwrap();
                    return;
                }
                v.resize(size, 0);
                sender.send(Msg::Data(v)).unwrap();
            }
        });
        let mut resp = loop {
            let now = Instant::now();
            if deadline < now {
                break Response::Error {
                    kind: ErrorResult::TimeLimitExceeded,
                };
            }
            match receiver.recv_timeout(deadline - now) {
                Ok(Msg::Data(data)) => output.extend_from_slice(&data),
                Ok(Msg::Fin(hwm, false)) => {
                    break Response::Test(TestResult {
                        output,
                        time: start_time.elapsed().as_secs_f64(),
                        memory_bytes: hwm,
                    })
                }
                Ok(Msg::Fin(_, true)) => {
                    break Response::Error {
                        kind: ErrorResult::OutputLimitExceeded,
                    }
                }
                Ok(Msg::Err) => {
                    break Response::Error {
                        kind: ErrorResult::RuntimeError,
                    }
                }
                _ => {
                    break Response::Error {
                        kind: ErrorResult::TimeLimitExceeded,
                    }
                }
            }
        };
        let status = match child.try_wait()? {
            Some(s) => s,
            None => {
                let _ = child.kill();
                child.wait()?
            }
        };
        handler.join().unwrap();
        let ignore_exit_status = match &resp {
            Response::Error {
                kind: ErrorResult::OutputLimitExceeded,
            }
            | Response::Error {
                kind: ErrorResult::TimeLimitExceeded,
            } => true,
            _ => false,
        };
        if !status.success() && !ignore_exit_status {
            if is_oom(status) {
                resp = Response::Error {
                    kind: ErrorResult::MemoryLimitExceeded,
                };
            } else {
                resp = Response::Error {
                    kind: ErrorResult::RuntimeError,
                };
            }
        }
        Ok(resp)
    }

    fn recv(&mut self) -> Result<Request> {
        let mut sz = [0u8; 4];
        self.reader.read_exact(&mut sz)?;
        self.buf.resize(u32::from_le_bytes(sz) as usize, 0);
        self.reader.read_exact(&mut self.buf)?;
        Ok(rmp_serde::from_slice(&self.buf).unwrap())
    }

    fn send(&mut self, v: &Response) -> Result<()> {
        let v = match rmp_serde::to_vec_named(v) {
            Ok(v) => v,
            Err(e) => return Err(Error::new(ErrorKind::InvalidData, e)),
        };
        let size_bytes = (v.len() as u32).to_le_bytes();
        self.writer.write_all(&size_bytes)?;
        self.writer.write_all(&v)?;
        self.writer.flush()?;
        Ok(())
    }
}

fn read_vm_hwm(path: &str) -> Result<u64> {
    let mut reader = BufReader::new(File::open(&path)?);
    let mut line = String::new();
    while reader.read_line(&mut line)? > 0 {
        if !line.starts_with("VmHWM:") {
            line.clear();
            continue;
        }
        let v = &line[6..].trim_start();
        let sz_kb: u64 = (&v[..v.find(' ').unwrap()]).parse().unwrap();
        return Ok(sz_kb * 1024);
    }
    Err(Error::new(ErrorKind::UnexpectedEof, ""))
}

fn is_oom(s: ExitStatus) -> bool {
    s.code().is_none() && s.signal().is_some() && s.signal().unwrap() == 9
}

impl<R: Read, W: Write> Drop for Agent<R, W> {
    fn drop(&mut self) {
        if let Some(cfg) = &self.config.compile {
            if !cfg.path.is_empty() {
                let _ = remove_file(&cfg.path);
            }
            let _ = remove_file(&cfg.output);
        }
        if let Some(cfg) = &self.config.test {
            if !cfg.path.is_empty() {
                let _ = remove_file(&cfg.path);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::*;
    use crate::models::*;
    use std::os::unix::net::UnixStream;

    fn get_compilation_config() -> CompilationConfig {
        CompilationConfig {
            path: String::new(),
            ext: ".rs".to_string(),
            output: String::new(),
            cmd: "rustc".to_string(),
            args: vec![
                "-O".to_string(),
                "-o".to_string(),
                "<output>".to_string(),
                "<path>".to_string(),
            ],
        }
    }

    fn get_test_config() -> TestConfig {
        TestConfig {
            path: String::new(),
            ext: String::new(),
            cmd: String::new(),
            args: Vec::new(),
        }
    }

    fn create_agent(config: Config) -> (Agent<UnixStream, UnixStream>, UnixStream) {
        let (pipe, pipe_agent) = UnixStream::pair().unwrap();
        (
            Agent::new(config, pipe_agent.try_clone().unwrap(), pipe_agent),
            pipe,
        )
    }

    fn compile(code: &str) -> Option<Vec<u8>> {
        let (mut agent, _) = create_agent(Config {
            compile: Some(get_compilation_config()),
            test: None,
        });
        let req = Compilation {
            code: code.as_bytes().to_vec(),
            time_limit: 10,
            memory_limit: 64,
        };
        match agent.process_compile(req) {
            Ok(v) => match v {
                Response::Compilation(c) => Some(c.binary),
                _ => None,
            },
            _ => None,
        }
    }

    #[test]
    fn compile_invalid_cmd() {
        // config.json の設定ミス.
        // レスポンスを返さずにAgentが氏にstdin/stdoutが切断される
        let mut ccfg = get_compilation_config();
        ccfg.cmd = "rustccccc".to_string();
        let (mut agent, _) = create_agent(Config {
            compile: Some(ccfg),
            test: None,
        });
        let req = Compilation {
            code: b"fn main() { println!(\"Hello World\"); }".to_vec(),
            time_limit: 10,
            memory_limit: 64,
        };
        assert!(agent.process_compile(req).is_err());
    }

    #[test]
    fn compile_invalid_path() {
        // config.json の設定ミス.
        // コンパイラは起動しエラーコードを返すのでコンパイルエラーとなる
        let mut ccfg = get_compilation_config();
        ccfg.args[2] = "/tmp/hoge.rs".to_string();
        let (mut agent, _) = create_agent(Config {
            compile: Some(ccfg),
            test: None,
        });
        let req = Compilation {
            code: b"fn main() { println!(\"Hello World\"); }".to_vec(),
            time_limit: 10,
            memory_limit: 64,
        };
        match agent.process_compile(req) {
            Ok(v) => match v {
                Response::Error { kind } => assert_eq!(kind, ErrorResult::CompilationError),
                _ => assert!(false),
            },
            _ => assert!(false),
        };
    }

    #[test]
    fn compile_invalid_code() {
        // コンパイルエラー
        let (mut agent, _) = create_agent(Config {
            compile: Some(get_compilation_config()),
            test: None,
        });
        let req = Compilation {
            code: b"INVALID RUST CODE".to_vec(),
            time_limit: 10,
            memory_limit: 64,
        };
        match agent.process_compile(req) {
            Ok(v) => match v {
                Response::Error { kind } => assert_eq!(kind, ErrorResult::CompilationError),
                _ => assert!(false),
            },
            _ => assert!(false),
        };
    }

    #[test]
    fn compile_ok() {
        // コンパイル成功
        let (mut agent, _) = create_agent(Config {
            compile: Some(get_compilation_config()),
            test: None,
        });
        let req = Compilation {
            code: b"fn main() { println!(\"Hello World\"); }".to_vec(),
            time_limit: 10,
            memory_limit: 64,
        };
        match agent.process_compile(req) {
            Ok(v) => match v {
                Response::Compilation(c) => {
                    assert!(c.binary.len() > 0);
                    assert!(c.time > 0.0);
                }
                _ => assert!(false),
            },
            _ => assert!(false),
        };
    }

    fn prepare<R: Read, W: Write>(
        agent: &mut Agent<R, W>,
        binary: Vec<u8>,
        time_limit: Option<u32>,
        memory_limit: Option<u32>,
    ) {
        let prep = Preparation {
            code: binary,
            time_limit: time_limit.unwrap_or(10),
            memory_limit: memory_limit.unwrap_or(64),
            output_limit: 1,
        };
        agent.process_prepare(prep).unwrap();
    }

    #[test]
    fn test_runtime_error() {
        // バイナリ実行時にエラー
        let binary = compile("fn main() { panic!(); }").unwrap();
        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, None, None);
        let req = TestRequest { input: vec![] };
        match agent.process_test(req) {
            Ok(Response::Error { kind }) => assert_eq!(kind, ErrorResult::RuntimeError),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_ok() {
        // テスト正常終了
        let binary = compile("fn main() { println!(\"Hello World\"); }").unwrap();
        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, None, None);
        let req = TestRequest { input: vec![] };
        match agent.process_test(req) {
            Ok(Response::Test(r)) => {
                assert_eq!(r.output, b"Hello World\n");
                assert!(r.time > 0.0);
            }
            _ => assert!(false),
        }
    }

    #[test]
    fn test_timeout() {
        // タイムアウト
        let binary = compile("use std::time::Duration;\nuse std::thread::sleep;\nfn main() { sleep(Duration::from_millis(1100)); }").unwrap();
        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, Some(1), None);
        let req = TestRequest { input: vec![] };
        match agent.process_test(req) {
            Ok(Response::Error { kind }) => assert_eq!(kind, ErrorResult::TimeLimitExceeded),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_memory_limit() {
        // メモリ制限超
        let code = "fn main() { let mut v: Vec<u8> = Vec::new();
            v.resize(1024 * 1024 * 1024, 1); let mut x = 0u64;
            for i in 0..v.len() { x += (v[i] + v[(i + x as usize) % v.len()]) as u64; }
            println!(\"{}\", x); }";
        let binary = compile(code).unwrap();

        // cgroup設定(パスワード不要なsudo権限が必要)
        let cgroups_dir = "/sys/fs/cgroup/memory/penguin_judge_tests";
        let limit_in_bytes = 2u32.pow(20) * 64; // 64MiB
        Command::new("sudo")
            .arg("bash").arg("-c").arg(
                format!(
                    "mkdir -p {}; echo {} > {}/memory.limit_in_bytes; echo {} > {}/memory.memsw.limit_in_bytes; echo {} > {}/cgroup.procs",
                    cgroups_dir,
                    limit_in_bytes,
                    cgroups_dir,
                    limit_in_bytes,
                    cgroups_dir,
                    get_pid(),
                    cgroups_dir,
                )).status().unwrap();

        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, None, Some(64));
        let req = TestRequest { input: vec![] };
        let ret = agent.process_test(req);
        Command::new("sudo")
            .arg("bash")
            .arg("-c")
            .arg(format!(
                "echo -1 > {}/memory.memsw.limit_in_bytes; echo -1 > {}/memory.limit_in_bytes",
                cgroups_dir, cgroups_dir,
            ))
            .status()
            .unwrap();
        match ret {
            Ok(Response::Error { kind }) => assert_eq!(kind, ErrorResult::MemoryLimitExceeded),
            _ => assert!(false),
        }
    }

    #[test]
    fn test_output_limit() {
        // 出力サイズ超過
        let binary =
            compile("fn main() { for i in 0..std::u64::MAX { println!(\"Hello {}\", i); }}")
                .unwrap();
        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, Some(1), None);
        let req = TestRequest { input: vec![] };
        match agent.process_test(req) {
            Ok(Response::Error { kind }) => assert_eq!(kind, ErrorResult::OutputLimitExceeded),
            v => {
                println!("{:?}", v);
                assert!(false)
            }
        }
    }

    #[test]
    fn test_hwm() {
        let path = "/proc/self/status".to_string();
        let ret = read_vm_hwm(&path).unwrap();
        assert!(ret > 0);
    }
}
