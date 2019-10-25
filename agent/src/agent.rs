use std::fs::{File, Permissions};
use std::io::{BufReader, BufWriter, Error, ErrorKind, Read, Result, Write};
use std::os::unix::fs::PermissionsExt;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread::spawn;
use std::time::{Duration, Instant};

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
    pub fn new(config: Config, reader: R, writer: W) -> Self {
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
        let compile_cfg = self.get_optional_config(&self.config.compile)?;
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
                                time: d.as_secs() as f64 + d.subsec_nanos() as f64 * 1e-9,
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
        let test_cfg = self.get_optional_config(&self.config.test)?;
        self.time_limit = config.time_limit;
        self.memory_limit = config.memory_limit;
        let mut f = File::create(&test_cfg.path)?;
        f.set_permissions(Permissions::from_mode(0o755))?;
        f.write_all(&config.code)
    }

    fn process_test(&mut self, req: TestRequest) -> Result<Response> {
        let test_cfg = self.get_optional_config(&self.config.test)?;
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
                        time: d.as_secs() as f64 + d.subsec_nanos() as f64 * 1e-9,
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

    fn get_optional_config<'a, T>(&self, o: &'a Option<T>) -> Result<&'a T> {
        match o {
            Some(v) => Ok(v),
            _ => Err(Error::new(ErrorKind::InvalidData, "test config required")),
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
