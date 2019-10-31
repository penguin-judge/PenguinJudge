mod agent;
mod config;
mod models;

use agent::Agent;
use config::Config;

fn main() {
    let config = Config::load_from_default_path();
    let mut agent = Agent::new(config, std::io::stdin(), std::io::stdout());
    agent.start().unwrap();
}
