#!/bin/sh
script_file=`readlink -f "$0"`
script_dir=`dirname "$script_file"`
trac_env="$script_dir/env"
trac_instance_config="$script_dir/instance"
trac_user='trac'
trac_group='trac'
gunicorn_num_workers=${GUNICORN_NUM_WORKERS:-2}
gunicorn_num_threads=${GUNICORN_NUM_THREADS:-2}
gunicorn_debug=${GUNICORN_DEBUG:-0}
gunicorn_opts=''
clear_env="${TRAC_CLEAR_ENV:-0}"

function upgrade() {
    local upgrade_ok=0

    # Apply the latest configuration from Docker
    trac-ini "$trac_env/conf/trac.ini" "trac" "base_url" "${TRAC_BASE_URL}"
    trac-ini "$trac_env/conf/trac.ini" "trac" "database" "${TRAC_DATABASE}"
    # enable Nginx sendfile support
    trac-ini "$trac_env/conf/trac.ini" "trac" "xsendfile_header" "X-Accel-Redirect"
    trac-ini "$trac_env/conf/trac.ini" "trac" "repository_sync_per_request" "disabled"
    trac-ini "$trac_env/conf/trac.ini" "versioncontrol" "default_repository_type" "git"
    trac-ini "$trac_env/conf/trac.ini" "git" "cached_repository" "enabled"

    trac-ini "$trac_env/conf/trac.ini" "project" "name" "${TRAC_PROJECT_NAME}"
    trac-ini "$trac_env/conf/trac.ini" "project" "descr" "${TRAC_PROJECT_DESCRIPTION}"
    trac-ini "$trac_env/conf/trac.ini" "project" "url" "${TRAC_BASE_URL}"
    trac-ini "$trac_env/conf/trac.ini" "project" "admin" "${TRAC_PROJECT_ADMIN}"

    # Only enable addons once
    if [ ! -f "$trac_env/addons_enabled" ]; then
        echo "done" > "$trac_env/addons_enabled"

        # allow anonymous to run admin page
        su -s /bin/sh -c "trac-admin \"$trac_env\" permission add anonymous TRAC_ADMIN" "$trac_user" || upgrade_ok=1

        trac-ini "$trac_env/conf/trac.ini" "components" "announcer.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "customfieldadmin.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "tracworkflowadmin.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "clients.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "HudsonTrac.HudsonTracPlugin.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "timingandestimationplugin.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "advancedworkflow.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "crashdump.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "iniadmin.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "mastertickets.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "tracrpc.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "logviewer.*" "enabled"
        trac-ini "$trac_env/conf/trac.ini" "components" "arsoft.trac.plugins.commitupdater.commit_updater.*" "enabled"

        trac-ini "$trac_env/conf/trac.ini" "components" "tracopt.versioncontrol.git.git_fs.*" "enabled"

        # fix missing font in workflow diagrams
        trac-ini "$trac_env/conf/trac.ini" "workflow-admin" "diagram_font" "Open Sans Regular"

    fi

    # always disable old navadd plugin
    trac-ini "$trac_env/conf/trac.ini" "components" "navadd.navadd.*" "disabled"

    if [ -f "$trac_instance_config" ]; then
        echo "Apply config changes from $trac_instance_config"
        trac-ini "$trac_env/conf/trac.ini" "$trac_instance_config"
    else
        echo "Instance config file $trac_instance_config unavailable"
    fi

    if [ $upgrade_ok -eq 0 ]; then
        su -s /bin/sh -c "trac-admin \"$trac_env\" upgrade --no-backup" "$trac_user" || upgrade_ok=1
        su -s /bin/sh -c "trac-admin \"$trac_env\" wiki upgrade" "$trac_user" || upgrade_ok=1
    fi

    # Remove multi site-in-site directories created by previous trac-admin deploy runs
    if [ -d "$trac_env/htdocs/site/site" ]; then
        echo "Remove directory $trac_env/htdocs/site/site"
        rm -rf "$trac_env/htdocs/site/site"
    fi

    if [ $upgrade_ok -eq 0 ]; then
        test -d "$trac_env/tmp/deploy" && rm -rf "$trac_env/tmp/deploy"
        # Create temp deploy directory and create a symlink for site to avoid trac-admin to create
        # a large number of site directories
        su -s /bin/sh -c "mkdir -p \"$trac_env/tmp/deploy/htdocs\"; ln -s . \"$trac_env/tmp/deploy/htdocs/site\"; trac-admin \"$trac_env\" deploy \"$trac_env/tmp/deploy\"" "$trac_user" || upgrade_ok=1
        if [ -f "$trac_env/tmp/deploy/htdocs/common/css/trac.css" ]; then
            echo "Copy trac static files to $trac_env/htdocs"
            # remove symlink to site directory to avoid trouble with customizations
            rm "$trac_env/tmp/deploy/htdocs/site"
            cp -a "$trac_env/tmp/deploy/htdocs"/* "$trac_env/htdocs"
        else
            echo "Deploy of $trac_env failed" 1>&2
        fi
        test -d "$trac_env/tmp/deploy" && rm -rf "$trac_env/tmp/deploy"
    fi

    if [ $upgrade_ok -eq 0 ]; then
        echo "Upgrade of $trac_env complete"
    else
        echo "Failed to upgrade $trac_env" 1>&2
    fi

    cat << EOF > /bin/run-trac-admin
#!/bin/sh
su -s /bin/sh -c "trac-admin $trac_env \$*" "$trac_user"
EOF
    chmod +x /bin/run-trac-admin
    return $upgrade_ok
}

function initenv() {
    local init_ok=0
    if [ ! -d "$trac_env" ]; then
        mkdir "$trac_env"
    fi
    if [ ! -d "$trac_env" ]; then
        echo "Failed to create directory $trac_env" 1>&2
        init_ok=1
    else
        chown "$trac_user:$trac_group" -R "$trac_env" || init_ok=1
        su -s /bin/sh -c "trac-admin \"$trac_env\" initenv \"${TRAC_PROJECT_NAME}\" \"${TRAC_DATABASE}\"" "$trac_user" || init_ok=1
    fi

    if [ $init_ok -eq 0 ]; then
        echo "Initialize of $trac_env complete"
    else
        rm -rf "$trac_env"/*
        echo "Failed to initialize $trac_env" 1>&2
    fi
    return $init_ok
}

function manage_repositories() {
    local manage_ok=0
    local run_sync=0
    echo "Setup repositories from ${TRAC_REPO_DIR}"
    trac-manage --config-repos "${TRAC_REPO_DIR}" "$trac_env" || manage_ok=1

    if [ "${TRAC_REPO_FORCE_SYNC}" -ne 0 ]; then
        run_sync=1
        echo "Repository sync forced"
    else
        if [ ! -f "${trac_env}/.repo_sync_done" ]; then
            run_sync=1
            echo "Initial repository sync triggered"
        fi
    fi
    if [ $run_sync -ne 0 ]; then
        set -x
        # Sync is very slow because of the following issue in trac 1.4; It's been improved for
        # trac 1.5.2 or later.
        # #13243: GitCachedRepository.sync() is slow
        # https://trac.edgewall.org/ticket/13243
        echo "Sync all configured repositories"
        local sync_start=$(date +"%s%N")
        trac-manage --sync-all-repos "$trac_env" || manage_ok=1
        #chown "$trac_user:$trac_group" -R "${TRAC_REPO_DIR}" || manage_ok=1
        local sync_end=$(date +"%s%N")
        local elappsed=$(((sync_end - sync_start)/1000000))
        set +x
        echo "Sync complete took ${elappsed}ms"
        touch "${trac_env}/.repo_sync_done"
    else
        echo "Repository sync skipped"
    fi
    return $manage_ok
}

function trac_env_perms() {

    local run_sync=0
    if [ ! -f "${trac_env}/.trac_env_perms" ]; then
        run_sync=1
        echo "Set trac environment permissions"
    fi
    if [ $run_sync -ne 0 ]; then
        set -x
        local sync_start=$(date +"%s%N")
        chown "$trac_user:$trac_group" -R "$trac_env"
        local sync_end=$(date +"%s%N")
        local elappsed=$(((sync_end - sync_start)/1000000))
        set +x
        echo "Setting trac environment permissions took ${elappsed}ms"
        touch "${trac_env}/.repo_sync_done"
    else
        echo "Setting trac environment permissions skipped"
    fi
    return 0
}

function startup_failure() {
    local RES=$?
    if [ $# -ne 0 ]; then
        echo "Startup failed with error code $RES at $*" 1>&2
    else
        echo "Startup failed with error code $RES" 1>&2
    fi
    exit $RES
}

if [ $clear_env -ne 0 ]; then
    echo "Clear environment $trac_env"
    find "$trac_env" -delete
fi

if [ ! -f "$trac_env/VERSION" ]; then
    echo "Initialize environment $trac_env"
    initenv || startup_failure
fi

trac_env_perms
echo "Upgrade environment $trac_env"
upgrade || startup_failure

manage_repositories || startup_failure

trac_uid=`id -u "$trac_user"`
echo "Run trac as using $trac_user/$trac_uid:$trac_group"

if [ $gunicorn_debug -ne 0 ]; then
    gunicorn_opts="$gunicorn_opts -R --capture-output --log-level=DEBUG"
fi

exec gunicorn --workers=${gunicorn_num_workers} --threads=${gunicorn_num_threads} $gunicorn_opts -b 0.0.0.0:8000 --user "$trac_user" --group "$trac_group" --chdir "$script_dir" trac_wsgi:application
exit $?
