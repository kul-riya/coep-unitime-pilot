#!/usr/bin/env sh
# Regenerate the Python gRPC stubs from ../src/main/proto/solver_env.proto.
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-.venv/bin/python}
$PY -m grpc_tools.protoc -I ../src/main/proto \
  --python_out=unitime_rl/proto --grpc_python_out=unitime_rl/proto --pyi_out=unitime_rl/proto \
  ../src/main/proto/solver_env.proto
# make the generated import relative to the package
sed -i 's/^import solver_env_pb2 as solver__env__pb2/from . import solver_env_pb2 as solver__env__pb2/' unitime_rl/proto/solver_env_pb2_grpc.py
echo "generated unitime_rl/proto/solver_env_pb2*.py"
