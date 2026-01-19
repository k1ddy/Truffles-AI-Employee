module.exports = {
    apps: [
        {
            name: 'console-web',
            cwd: '/home/zhan/truffles-main/console-web',
            script: 'npm',
            args: 'run dev -- -H 0.0.0.0',
            interpreter: 'none',
            env: {
                NODE_ENV: 'development',
                PORT: 3000
            },
            watch: false,
            autorestart: true,
            max_restarts: 10,
            restart_delay: 5000,
            log_date_format: 'YYYY-MM-DD HH:mm:ss',
            error_file: '/home/zhan/logs/console-web-error.log',
            out_file: '/home/zhan/logs/console-web-out.log',
            merge_logs: true
        }
    ]
};
