#!/bin/sh
# Clone a category's central benchmarks repo on the node, then report back.
#
# Clones ${repository} @ ${hash} into /home/ubuntu/benchmarks_repo (kept in sync with
# arch_comp/benchmarks.py CLONE_DIR). The load step then reads its instances.csv back
# over SSH and fans it into the category's benchmarks. The remote script POSTs the log
# tail to ${ROOT_URL}/update/${task_id}/success|failure, so a clone error is captured in
# the DB even after the node is torn down.
#
# Params (env, from the step handler): benchmark_ip task_id repository hash.
# ROOT_URL comes from the backend environment. NODE_SSH_KEY locates the node key.
set -eu

ssh_key="${NODE_SSH_KEY:-$HOME/.ssh/vnncomp.pem}"
clone_dir="/home/ubuntu/benchmarks_repo"
remote_script_path="/home/ubuntu/load_benchmark_${task_id}.sh"
remote_log_path="/home/ubuntu/logs/load.log"

ssh -o StrictHostKeyChecking=accept-new -i "${ssh_key}" "ubuntu@${benchmark_ip}" \
    "cat > ${remote_script_path} <<'REMOTE_SCRIPT'
#!/bin/bash
cd /home/ubuntu || exit 1
mkdir -p logs
exec > >(tee ${remote_log_path}) 2>&1
set -x
echo '[INFO] benchmark load started'

report() {  # success|failure — POST the log tail so the error is captured even after teardown
    tail -c 200000 ${remote_log_path} > /tmp/load_${task_id}.tail 2>/dev/null || true
    curl --retry 100 --retry-connrefused --max-time 120 --data-binary @/tmp/load_${task_id}.tail ${ROOT_URL}/update/${task_id}/\$1 || true
    return 0
}

rm -rf ${clone_dir} \
    && git clone ${repository} ${clone_dir} \
    && if [ -n \"${hash}\" ]; then git -C ${clone_dir} checkout ${hash}; fi \
    && ls ${clone_dir}/instances.csv \
    && report success \
    || report failure
REMOTE_SCRIPT
chmod +x ${remote_script_path}
tmux new-session -d -s load /bin/bash ${remote_script_path}"
