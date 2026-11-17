# A browser login for a tool on a node

Some tools log in through a browser, such as rclone's Google login, which the data runs of
November 2026 redid daily. The tool listens on a port on the node, and the login page sends the
user's browser back to `127.0.0.1:<port>`. An ssh tunnel carries that request from the browser's
machine to the node.

The agent holds the tunnel. Asking the user to hold an `ssh -L` open in another terminal costs
them a step, and a command they run with the `!` prefix cannot hold one. This recipe worked 3
times:

1. Hold the tunnel in the background (the shell tool's background mode), to the node the tool
   runs on. The port is the one the tool listens on, 53682 for rclone:

   ```bash
   ssh -N -o ExitOnForwardFailure=yes -L <port>:127.0.0.1:<port> <node>
   ```

   If it exits at once, something on this machine already holds the port.
2. Start the login detached on the node, with its output in a log
   (`remote-processes.md`, "Start a process detached"). It runs with no terminal, so pass any
   answers it would ask for as flags. For rclone, run it with the `RCLONE_CONFIG` the job reads,
   or the job keeps the old token.
3. Read the log for the login link, and send the link to the user, to open in a browser on the
   machine that holds the tunnel.
4. When the log reports success, stop the tunnel and the login process if it still runs, and
   check that the tool works.
