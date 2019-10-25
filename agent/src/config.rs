use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct CompilationConfig {
    pub path: String,
    pub output: String,
    pub cmd: String,
    #[serde(default)]
    pub args: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TestConfig {
    pub path: String,
    pub cmd: String,
    #[serde(default)]
    pub args: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Config {
    pub compile: Option<CompilationConfig>,
    pub test: Option<TestConfig>,
}

impl Config {
    pub fn load<T: AsRef<Path>>(path: T) -> Config {
        let file = File::open(path).unwrap();
        let reader = BufReader::new(file);
        serde_json::from_reader(reader).unwrap()
    }

    pub fn load_from_default_path() -> Config {
        let path = match std::env::var_os("PENGUIN_JUDGE_AGENT_CONFIG") {
            Some(v) => v.into_string().unwrap(),
            None => "/config.json".to_string(),
        };
        Config::load(&path)
    }
}
