import { registerAs } from '@nestjs/config';

export default registerAs('jwt', () => ({
  secret: process.env.JWT_SECRET || 'money-jwt-secret-change-me',
  refreshTokenSecret:
    process.env.REFRESH_TOKEN_SECRET || 'money-refresh-secret-change-me',
  accessTokenExpiresIn: process.env.JWT_ACCESS_EXPIRES_IN || '15m',
  refreshTokenExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d',
  saltRounds: parseInt(process.env.SALT_ROUNDS ?? '10', 10),
}));
