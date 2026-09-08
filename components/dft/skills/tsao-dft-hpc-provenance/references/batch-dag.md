# Batch DAG and Slurm Arrays

Tasks declare dependencies, owner directory, expected artifacts, retry limit and acceptance gate. Independent jobs may run concurrently; dependent tasks cannot infer completion from file timestamps alone.

For homogeneous independent Slurm work, prefer one reviewed base manifest plus `generate_job_array.py` and a JSONL task table. The array `%` limit is an explicit concurrency ceiling. Every task retains a unique ID, input, work directory, stdout and stderr path.

Use separate scripts or a workflow DAG instead when tasks differ in resources, executable, environment, method fingerprint or dependency structure. Script generation never implies submission approval.
