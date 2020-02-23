#!/bin/sh
script_file=`readlink -f "$0"`
script_dir=`dirname "$script_file"`
trac_env="$script_dir/env"
trac_user='trac'
gunicorn_num_workers=1

function upgrade() {

    trac-ini "$trac_env/conf/trac.ini" "components" "announcer.*" "enabled"
    trac-ini "$trac_env/conf/trac.ini" "components" "customfieldadmin.*" "enabled"
    trac-ini "$trac_env/conf/trac.ini" "components" "tracworkflowadmin.*" "enabled"
    trac-ini "$trac_env/conf/trac.ini" "components" "clients.*" "enabled"

    su -s /bin/sh -c "trac-admin \"$trac_env\" upgrade" "$trac_user"
    su -s /bin/sh -c "trac-admin \"$trac_env\" wiki upgrade" "$trac_user"

    test -d "$trac_env/tmp/deploy" && rm -rf "$trac_env/tmp/deploy"
    su -s /bin/sh -c "trac-admin \"$trac_env\" deploy \"$trac_env/tmp/deploy\"" "$trac_user"
    cp -a "$trac_env/tmp/deploy/htdocs"/* "$trac_env/htdocs"
    rm -rf "$trac_env/tmp/deploy"
    echo "Upgrade of $trac_env complete"

    cat << EOF > /bin/run-trac-admin
#!/bin/sh
su -s /bin/sh -c "trac-admin $trac_env \$*" "$trac_user"
EOF
    chmod +x /bin/run-trac-admin
}

function initenv() {
    local init_args="example sqlite:db/trac.db"
    [ ! -d "$trac_env" ] && mkdir "$trac_env"
    chown "$trac_user:nogroup" -R "$trac_env"
    su -s /bin/sh -c "trac-admin \"$trac_env\" initenv $init_args" "$trac_user"
}

if [ ! -f "$trac_env/VERSION" ]; then
    initenv || exit $?
fi

chown "$trac_user:nogroup" -R "$trac_env"
upgrade
exec gunicorn -w${gunicorn_num_workers} -R --capture-output -b 0.0.0.0:8000 -n "trac" --log-level=DEBUG --user "$trac_user" --group "nogroup" --chdir "$script_dir" trac_wsgi:application
exit $?
