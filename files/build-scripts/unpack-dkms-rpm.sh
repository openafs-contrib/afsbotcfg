#!/bin/bash
set -e
set -x

DKMS_OPENAFS=$(echo $(pwd)/packages/rpmbuild/RPMS/x86_64/dkms-openafs-*.rpm)
if [[ ! -f "$DKMS_OPENAFS" ]]; then
    echo "dkms-openafs rpm is missing: $DKMS_OPENAFS" >&2
    exit 1
fi

mkdir -p packages/dkms
cd packages/dkms
rpm2cpio "$DKMS_OPENAFS" | cpio -dium --quiet

cd usr/src
BUILD=$(echo openafs-*)
if [[ ! -d "$BUILD" ]]; then
    echo "dkms-openafs build directory is missing: $BUILD" >&2
    exit 1
fi
ln -s $BUILD openafs
