import 'reflect-metadata';
import { config as loadEnv } from 'dotenv';
import { DataSource } from 'typeorm';
import { User } from '../modules/users/entities/user.entity';
import { Category } from '../modules/categories/entities/category.entity';
import { Transaction } from '../modules/transactions/entities/transaction.entity';
import { Budget } from '../modules/budgets/entities/budget.entity';

loadEnv();

/**
 * DataSource độc lập dùng cho script seed / CLI (ngoài runtime NestJS).
 */
export const AppDataSource = new DataSource({
  type: 'postgres',
  host: process.env.DB_HOST || '127.0.0.1',
  port: parseInt(process.env.DB_PORT ?? '5432', 10),
  username: process.env.DB_USERNAME || 'money',
  password: process.env.DB_PASSWORD || 'money',
  database: process.env.DB_DATABASE || 'money_manager',
  entities: [User, Category, Transaction, Budget],
  synchronize: true,
  logging: false,
});
