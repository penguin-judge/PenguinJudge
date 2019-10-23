use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct Compilation {
    pub code: Vec<u8>,
    pub time_limit: u32,
    pub memory_limit: u32,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CompilationResult {
    pub binary: Vec<u8>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Preparation {
    pub code: Vec<u8>,
    pub time_limit: u32,
    pub memory_limit: u32,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "type")]
pub enum Request {
    Compilation(Compilation),
    Preparation(Preparation),
    Test(TestRequest),
    Fin,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TestRequest {
    pub input: Vec<u8>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TestResult {
    pub output: Vec<u8>,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum ErrorResult {
    CompilationError,
    RuntimeError,
    MemoryLimitExceeded,
    TimeLimitExceeded,
    OutputLimitExceeded,
    InternalError,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "type")]
pub enum Response {
    Compilation(CompilationResult),
    Test(TestResult),
    Error(ErrorResult),
}
