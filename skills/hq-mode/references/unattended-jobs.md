# Unattended jobs

These rules cover a job that keeps running after the session ends, or through a night nobody
watches. The lab sets up no failure alert. Once the session ends, watching the job is the
user's job, by whatever means suits the run.

- **Read the log of each unattended step's first run:** the first copy a job makes on its
  own, the first successor job to start, the first scheduled pass. An exit code is not
  enough. Report nothing to the user as working until you have read its log.
- **Set every environment variable the job needs in its script,** a tool's config path
  among them. `sbatch` passes the submitting shell's environment into the job by default,
  so a job that ran from your shell can fail when a successor or a scheduler submits it.
- **A long job that writes to a shared disk checks free space as it runs,** and stops
  cleanly below a floor set in its script.
- **Keep the Mac awake on a headless night** with `caffeinate`.
- **Fetch a large remote file once.** When the run needs it twice, save it with its date in
  the run's [work folder](playbooks/cluster-run.md#work-folder).
- **Before the session ends, tell the user which jobs keep running unwatched,** by job ID
  and cluster.
