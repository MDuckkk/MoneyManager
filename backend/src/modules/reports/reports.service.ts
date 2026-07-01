import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Transaction } from '../transactions/entities/transaction.entity';
import { CategoryType } from '../categories/entities/category-type.enum';
import { ByCategoryQueryDto, ReportQueryDto } from './dto/reports.dto';

@Injectable()
export class ReportsService {
  constructor(
    @InjectRepository(Transaction)
    private readonly transactionsRepository: Repository<Transaction>,
  ) {}

  private ok(data: unknown, message = 'Success') {
    return { success: true, message, data };
  }

  async summary(userId: number, query: ReportQueryDto) {
    const { month, year } = this.resolvePeriod(query);
    const prev = this.previousPeriod(month, year);

    const [current, previous] = await Promise.all([
      this.totals(userId, month, year),
      this.totals(userId, prev.month, prev.year),
    ]);

    const expenseChangePct =
      previous.expense > 0
        ? Math.round(
            ((current.expense - previous.expense) / previous.expense) * 100,
          )
        : null;
    const incomeChangePct =
      previous.income > 0
        ? Math.round(
            ((current.income - previous.income) / previous.income) * 100,
          )
        : null;

    return this.ok({
      month,
      year,
      income: current.income,
      expense: current.expense,
      balance: current.income - current.expense,
      previousMonth: {
        income: previous.income,
        expense: previous.expense,
      },
      incomeChangePct,
      expenseChangePct,
    });
  }

  async byCategory(userId: number, query: ByCategoryQueryDto) {
    const { month, year } = this.resolvePeriod(query);
    const type = query.type ?? CategoryType.EXPENSE;
    const { start, end } = this.monthRange(year, month);

    const rows = await this.transactionsRepository
      .createQueryBuilder('tx')
      .leftJoin('tx.category', 'category')
      .select('category.id', 'categoryId')
      .addSelect('category.name', 'categoryName')
      .addSelect('category.icon', 'icon')
      .addSelect('category.color', 'color')
      .addSelect('SUM(tx.amount)', 'total')
      .where('tx.user_id = :userId', { userId })
      .andWhere('tx.type = :type', { type })
      .andWhere('tx.occurred_at >= :start AND tx.occurred_at <= :end', {
        start,
        end,
      })
      .groupBy('category.id')
      .addGroupBy('category.name')
      .addGroupBy('category.icon')
      .addGroupBy('category.color')
      .orderBy('total', 'DESC')
      .getRawMany<{
        categoryId: number;
        categoryName: string;
        icon: string;
        color: string;
        total: string;
      }>();

    const items = rows.map((r) => ({
      categoryId: Number(r.categoryId),
      categoryName: r.categoryName,
      icon: r.icon,
      color: r.color,
      total: parseFloat(r.total),
    }));
    const grandTotal = items.reduce((sum, i) => sum + i.total, 0);

    return this.ok({ month, year, type, grandTotal, items });
  }

  private async totals(userId: number, month: number, year: number) {
    const { start, end } = this.monthRange(year, month);
    const rows = await this.transactionsRepository
      .createQueryBuilder('tx')
      .select('tx.type', 'type')
      .addSelect('SUM(tx.amount)', 'total')
      .where('tx.user_id = :userId', { userId })
      .andWhere('tx.occurred_at >= :start AND tx.occurred_at <= :end', {
        start,
        end,
      })
      .groupBy('tx.type')
      .getRawMany<{ type: CategoryType; total: string }>();

    let income = 0;
    let expense = 0;
    for (const row of rows) {
      if (row.type === CategoryType.INCOME) income = parseFloat(row.total);
      if (row.type === CategoryType.EXPENSE) expense = parseFloat(row.total);
    }
    return { income, expense };
  }

  private resolvePeriod(query: ReportQueryDto) {
    const now = new Date();
    return {
      month: query.month ?? now.getMonth() + 1,
      year: query.year ?? now.getFullYear(),
    };
  }

  private previousPeriod(month: number, year: number) {
    return month === 1
      ? { month: 12, year: year - 1 }
      : { month: month - 1, year };
  }

  private monthRange(year: number, month: number) {
    const pad = (n: number) => String(n).padStart(2, '0');
    const start = `${year}-${pad(month)}-01`;
    const lastDay = new Date(year, month, 0).getDate();
    const end = `${year}-${pad(month)}-${pad(lastDay)}`;
    return { start, end };
  }
}
