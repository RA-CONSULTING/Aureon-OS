module.exports = {
  apps: [
    {
      name: 'aureon-status',
      script: 'npx',
      args: 'tsx scripts/statusServer.ts',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        STATUS_PORT: 3001
      },
      error_file: './logs/status-error.log',
      out_file: './logs/status-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'hummingbird',
      script: 'npx',
      args: 'tsx scripts/hummingbird.ts',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        BOT_NAME: 'Hummingbird'
      },
      error_file: './logs/hummingbird-error.log',
      out_file: './logs/hummingbird-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'armyants',
      script: 'npx',
      args: 'tsx scripts/armyAnts.ts',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        BOT_NAME: 'ArmyAnts'
      },
      error_file: './logs/armyants-error.log',
      out_file: './logs/armyants-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'lonewolf',
      script: 'npx',
      args: 'tsx scripts/loneWolf.ts',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
        BOT_NAME: 'LoneWolf'
      },
      error_file: './logs/lonewolf-error.log',
      out_file: './logs/lonewolf-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
