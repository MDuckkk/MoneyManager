import * as bcrypt from 'bcrypt';
import { AppDataSource } from './data-source';
import { User } from '../modules/users/entities/user.entity';
import { Category } from '../modules/categories/entities/category.entity';
import { Transaction } from '../modules/transactions/entities/transaction.entity';
import { Budget } from '../modules/budgets/entities/budget.entity';
import { CategoryType } from '../modules/categories/entities/category-type.enum';
import { TransactionSource } from '../modules/transactions/entities/transaction-source.enum';
import { DEFAULT_CATEGORIES } from '../modules/categories/constants/default-categories';

const DEMO_EMAIL = 'demo@money.app';
const DEMO_PASSWORD = 'password123';

const pad = (n: number) => String(n).padStart(2, '0');
const dateStr = (y: number, m: number, d: number) =>
  `${y}-${pad(m)}-${pad(d)}`;

async function seed() {
  await AppDataSource.initialize();
  const users = AppDataSource.getRepository(User);
  const categories = AppDataSource.getRepository(Category);
  const transactions = AppDataSource.getRepository(Transaction);
  const budgets = AppDataSource.getRepository(Budget);

  let user = await users.findOne({ where: { email: DEMO_EMAIL } });
  if (!user) {
    user = await users.save(
      users.create({
        email: DEMO_EMAIL,
        passwordHash: await bcrypt.hash(DEMO_PASSWORD, 10),
        name: 'Demo User',
      }),
    );
  }

  let cats = await categories.find({ where: { userId: user.id } });
  if (cats.length === 0) {
    cats = await categories.save(
      DEFAULT_CATEGORIES.map((c) => categories.create({ ...c, userId: user.id })),
    );
  }

  const byName = (name: string) => cats.find((c) => c.name === name)!;
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const prev = m === 1 ? { y: y - 1, m: 12 } : { y, m: m - 1 };

  const existing = await transactions.count({ where: { userId: user.id } });
  if (existing === 0) {
    const make = (
      name: string,
      amount: number,
      day: number,
      note: string,
      period = { y, m },
    ) => {
      const cat = byName(name);
      return transactions.create({
        userId: user.id,
        categoryId: cat.id,
        type: cat.type,
        amount,
        note,
        occurredAt: dateStr(period.y, period.m, day),
        source: TransactionSource.MANUAL,
      });
    };

    await transactions.save([
      // Tháng hiện tại
      make('Lương', 20000000, 1, 'Lương tháng'),
      make('Thưởng', 2000000, 2, 'Thưởng dự án'),
      make('Ăn uống', 150000, 3, 'Ăn trưa'),
      make('Ăn uống', 250000, 5, 'Đi ăn cùng bạn'),
      make('Di chuyển', 50000, 4, 'Grab'),
      make('Di chuyển', 600000, 7, 'Đổ xăng'),
      make('Hóa đơn', 1200000, 8, 'Tiền điện nước'),
      make('Mua sắm', 800000, 6, 'Áo khoác'),
      make('Giải trí', 300000, 9, 'Xem phim'),
      make('Sức khỏe', 450000, 10, 'Khám sức khỏe'),
      // Tháng trước (để có dữ liệu so sánh)
      make('Lương', 18000000, 1, 'Lương tháng', prev),
      make('Ăn uống', 2200000, 12, 'Ăn uống tháng trước', prev),
      make('Di chuyển', 900000, 15, 'Di chuyển tháng trước', prev),
      make('Mua sắm', 1500000, 20, 'Mua sắm tháng trước', prev),
    ]);

    await budgets.save([
      budgets.create({
        userId: user.id,
        categoryId: byName('Ăn uống').id,
        month: m,
        year: y,
        limitAmount: 3000000,
      }),
      budgets.create({
        userId: user.id,
        categoryId: byName('Di chuyển').id,
        month: m,
        year: y,
        limitAmount: 1000000,
      }),
      budgets.create({
        userId: user.id,
        categoryId: byName('Mua sắm').id,
        month: m,
        year: y,
        limitAmount: 1000000,
      }),
    ]);
  }

  console.log('✅ Seed hoàn tất.');
  console.log(`   Tài khoản demo: ${DEMO_EMAIL} / ${DEMO_PASSWORD}`);
  await AppDataSource.destroy();
}

seed().catch((err) => {
  console.error('❌ Seed thất bại:', err);
  process.exit(1);
});
