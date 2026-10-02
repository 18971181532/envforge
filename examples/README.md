# EnvForge Examples

Try EnvForge in this directory:

```bash
# Initialize
envforge init

# Capture your environment
envforge capture dev-machine

# List profiles
envforge list

# View details
envforge show dev-machine

# Check for drift
envforge diff dev-machine

# Generate a bootstrap script for a new machine
envforge bootstrap dev-machine --shell bash

# Start the web dashboard
envforge serve --port 8765
```
