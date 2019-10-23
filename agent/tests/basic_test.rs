extern crate penguin_judge_agent;

use std::fs::File;
use std::os::unix::net::UnixStream;
use std::thread::spawn;
use std::io::{Read, Write};

use penguin_judge_agent::*;

#[test]
fn test_rust() {
    let code = "fn main() {
        let mut str = String::new();
        std::io::stdin().read_line(&mut str).unwrap();
        let x = str.trim().parse::<i32>().unwrap();
        println!(\"{}\", x + 1);
    }".as_bytes();
    let code_path = "/tmp/penguin_judge_agent_test.rs";
    let exec_path = "/tmp/penguin_judge_agent_test";
    let config_path = "/tmp/penguin_judge_agent_test.config";
    std::env::set_var("PENGUIN_JUDGE_AGENT_CONFIG", config_path);
    let binary: Vec<u8> = {
        let cconfig = Config {
            compile: Some(CompilationConfig {
                path: code_path.to_string(),
                cmd: "rustc".to_string(),
                args: vec!["-o".to_string(), exec_path.to_string(), code_path.to_string()],
                output: exec_path.to_string(),
            }),
            test: None
        };
        {
            let f = File::create(config_path).unwrap();
            serde_json::to_writer(f, &cconfig).unwrap();
        }
        let (mut pipe, pipe_agent) = UnixStream::pair().unwrap();
        let handler = spawn(move || {
            let mut agent = Agent::new(
                pipe_agent.try_clone().unwrap(), pipe_agent);
            agent.start().unwrap();
        });
        let mut output = Vec::new();
        let req = Request::Compilation(Compilation {
            code: code.to_vec(),
            time_limit: 30,
            memory_limit: 1024 * 1024 * 1024,
        });
        let req_bytes = rmp_serde::to_vec_named(&req).unwrap();
        pipe.write_all(&(req_bytes.len() as u32).to_le_bytes()).unwrap();
        pipe.write_all(&req_bytes).unwrap();
        pipe.flush().unwrap();
        let mut sz = [0u8; 4];
        pipe.read_exact(&mut sz).unwrap();
        output.resize(u32::from_le_bytes(sz) as usize, 0);
        pipe.read_exact(&mut output).unwrap();
        handler.join().unwrap();
        match rmp_serde::from_slice(&output).unwrap() {
            Response::Compilation(v) => v.binary,
            _ => panic!(),
        }
    };
    {
        let tconfig = Config {
            compile: None,
            test: Some(TestConfig {
                path: exec_path.to_string(),
                cmd: exec_path.to_string(),
                args: Vec::new(),
            }),
        };
        {
            let f = File::create(config_path).unwrap();
            serde_json::to_writer(f, &tconfig).unwrap();
        }
        let (mut pipe, pipe_agent) = UnixStream::pair().unwrap();
        let handler = spawn(move || {
            let mut agent = Agent::new(
                pipe_agent.try_clone().unwrap(), pipe_agent);
            agent.start().unwrap();
        });
        let mut output = Vec::new();
        {
            let req = Request::Preparation(Preparation {
                code: binary,
                time_limit: 10,
                memory_limit: 1024 * 1024 * 1024,
            });
            let req_bytes = rmp_serde::to_vec_named(&req).unwrap();
            pipe.write_all(&(req_bytes.len() as u32).to_le_bytes()).unwrap();
            pipe.write_all(&req_bytes).unwrap();
        }
        {
            let req = Request::Test(TestRequest {
                input: "1\n".to_string().into_bytes(),
            });
            let req_bytes = rmp_serde::to_vec_named(&req).unwrap();
            pipe.write_all(&(req_bytes.len() as u32).to_le_bytes()).unwrap();
            pipe.write_all(&req_bytes).unwrap();
        }
        pipe.flush().unwrap();
        let mut sz = [0u8; 4];
        pipe.read_exact(&mut sz).unwrap();
        output.resize(u32::from_le_bytes(sz) as usize, 0);
        pipe.read_exact(&mut output).unwrap();
        let resp = match rmp_serde::from_slice(&output).unwrap() {
            Response::Test(v) => v,
            Response::Error(e) => panic!("{:?}", e),
            e => panic!(e),
        };
        println!("{:?}", resp);
        {
            let req = Request::Fin;
            let req_bytes = rmp_serde::to_vec_named(&req).unwrap();
            pipe.write_all(&(req_bytes.len() as u32).to_le_bytes()).unwrap();
            pipe.write_all(&req_bytes).unwrap();
        }
        handler.join().unwrap();
    }
}
