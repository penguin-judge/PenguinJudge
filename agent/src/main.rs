mod agent;
mod config;
mod models;

use agent::Agent;

fn main() {
    let mut agent = Agent::new(std::io::stdin(), std::io::stdout());
    agent.start().unwrap();
}
