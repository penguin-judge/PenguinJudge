use std::collections::hash_map::DefaultHasher;
use std::fs::{remove_file, File, Permissions};
use std::hash::{Hash, Hasher};
use std::io::{BufReader, BufWriter, Error, ErrorKind, Read, Result, Write};
use std::os::unix::fs::PermissionsExt;
use std::process::{id as get_pid, Command, Stdio};
use std::sync::{Arc, Mutex};
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
                                time: d.as_secs() as f64 + f64::from(d.subsec_nanos()) * 1e-9,
                            }));
                        }
                    }
                }
                Ok(Response::Error {
                    kind: ErrorResult::CompilationError,
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
        let output = Arc::new(Mutex::new(Vec::new()));
        let start_time = Instant::now();
        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()?;
        let mut child_stdin = child.stdin.take().unwrap();
        let mut child_stdout = child.stdout.take().unwrap();
        let child_output = output.clone();
        let handler = spawn(move || {
            let mut buf = [0u8; 1024];
            if child_stdin.write_all(&req.input).is_err() || child_stdin.flush().is_err() {
                return;
            }
            loop {
                let size = match child_stdout.read(&mut buf) {
                    Ok(0) | Err(_) => break,
                    Ok(s) => s,
                };
                child_output
                    .lock()
                    .unwrap()
                    .extend_from_slice(&buf[0..size]);
            }
        });
        match child.wait_timeout(timeout)? {
            Some(status) => {
                handler.join().unwrap();
                let d = Instant::now().duration_since(start_time);
                if status.success() {
                    return Ok(Response::Test(TestResult {
                        output: output.lock().unwrap().clone(),
                        time: d.as_secs() as f64 + f64::from(d.subsec_nanos()) * 1e-9,
                    }));
                }
                Ok(Response::Error {
                    kind: ErrorResult::RuntimeError,
                })
            }
            None => {
                child.kill()?;
                child.wait()?;
                handler.join().unwrap();
                Ok(Response::Error {
                    kind: ErrorResult::TimeLimitExceeded,
                })
            }
        }
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


    /*
    #[test]
    fn test_memory_limit() {
        // メモリ制限超
        let binary = compile("fn main() {
  let mut v: Vec<u8> = Vec::new();
  v.resize(1024 * 1024 * 128, 1);
  let mut x = 0u64;
  for i in 0..v.len() {
    x += v[i] as u64;
  }
  println!(\"{}\", x);
}").unwrap();
        let (mut agent, _) = create_agent(Config {
            compile: None,
            test: Some(get_test_config()),
        });
        prepare(&mut agent, binary, None, Some(64));
        let req = TestRequest { input: vec![] };
        match agent.process_test(req) {
            Ok(Response::Error{kind}) => assert_eq!(kind, ErrorResult::MemoryLimitExceeded),
            _ => assert!(false),
        }
    }*/
}
