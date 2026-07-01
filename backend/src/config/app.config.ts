import { registerAs } from '@nestjs/config';

export default registerAs('app', () => ({
  nodeEnv: process.env.NODE_ENV || 'dev',
  port: parseInt(process.env.PORT ?? '9998', 10),
  whitelistDomains: process.env.WHITELIST_DOMAINS?.split(',') || [
    'http://localhost:5173',
    'http://localhost:3000',
  ],
}));
