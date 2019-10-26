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
