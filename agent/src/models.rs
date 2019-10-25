use serde::{Deserialize, Serialize, Serializer};
use std::io::Write;

#[derive(Serialize, Deserialize, Debug)]
pub struct Compilation {
    #[serde(with = "serde_bytes")]
    pub code: Vec<u8>,
    pub time_limit: u32,
    pub memory_limit: u32,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CompilationResult {
    #[serde(with = "serde_bytes")]
    pub binary: Vec<u8>,
    pub time: f64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Preparation {
    #[serde(with = "serde_bytes")]
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
    #[serde(with = "serde_bytes")]
    pub input: Vec<u8>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TestResult {
    #[serde(with = "serde_bytes")]
    pub output: Vec<u8>,
    pub time: f64,
}

#[derive(Deserialize, Debug)]
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
    Error { kind: ErrorResult },
}

impl Serialize for ErrorResult {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let mut v: Vec<u8> = Vec::new();
        write!(&mut v, "{:?}", self).unwrap();
        let s = String::from_utf8(v).unwrap();
        serializer.serialize_str(&s)
    }
}
