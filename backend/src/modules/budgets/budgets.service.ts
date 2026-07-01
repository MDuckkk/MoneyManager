import {
  BadRequestException,
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Budget } from './entities/budget.entity';
import { Category } from '../categories/entities/category.entity';
import { Transaction } from '../transactions/entities/transaction.entity';
import { CategoryType } from '../categories/entities/category-type.enum';
import {
  CreateBudgetDto,
  QueryBudgetsDto,
  UpdateBudgetDto,
} from './dto/budgets.dto';
import {
  computeBudgetPercentage,
  computeBudgetStatus,
} from './utils/budget-status.util';

@Injectable()
export class BudgetsService {
  constructor(
    @InjectRepository(Budget)
    private readonly budgetsRepository: Repository<Budget>,
    @InjectRepository(Category)
    private readonly categoriesRepository: Repository<Category>,
    @InjectRepository(Transaction)
    private readonly transactionsRepository: Repository<Transaction>,
  ) {}

  private ok(data: unknown, message = 'Success') {
    return { success: true, message, data };
  }

  async list(userId: number, query: QueryBudgetsDto) {
    const { month, year } = this.resolvePeriod(query);
    const budgets = await this.budgetsRepository.find({
      where: { userId, month, year },
      relations: { category: true },
      order: { id: 'DESC' },
    });
    return this.ok(budgets);
  }

  async create(userId: number, dto: CreateBudgetDto) {
    const category = await this.requireExpenseCategory(userId, dto.categoryId);

    const duplicate = await this.budgetsRepository.findOne({
      where: {
        userId,
        categoryId: category.id,
        month: dto.month,
        year: dto.year,
      },
    });
    if (duplicate) {
      throw new ConflictException(
        'Đã tồn tại ngân sách cho danh mục này trong tháng đã chọn',
      );
    }

    const budget = await this.budgetsRepository.save(
      this.budgetsRepository.create({
        userId,
        categoryId: category.id,
        month: dto.month,
        year: dto.year,
        limitAmount: dto.limitAmount,
      }),
    );

    return this.ok(
      await this.budgetsRepository.findOne({
        where: { id: budget.id },
        relations: { category: true },
      }),
      'Tạo ngân sách thành công',
    );
  }

  async update(userId: number, id: number, dto: UpdateBudgetDto) {
    const budget = await this.findOwned(userId, id);
    budget.limitAmount = dto.limitAmount;
    await this.budgetsRepository.save(budget);
    return this.ok(
      await this.budgetsRepository.findOne({
        where: { id },
        relations: { category: true },
      }),
      'Cập nhật ngân sách thành công',
    );
  }

  async remove(userId: number, id: number) {
    const budget = await this.findOwned(userId, id);
    await this.budgetsRepository.remove(budget);
    return this.ok(null, 'Xóa ngân sách thành công');
  }

  /**
   * Tiến độ ngân sách: với mỗi ngân sách của tháng, tính tổng đã chi của danh mục đó
   * rồi sinh trạng thái SAFE / WARNING / EXCEEDED.
   */
  async status(userId: number, query: QueryBudgetsDto) {
    const { month, year } = this.resolvePeriod(query);

    const budgets = await this.budgetsRepository.find({
      where: { userId, month, year },
      relations: { category: true },
    });

    const spentByCategory = await this.spentByCategory(userId, month, year);

    const items = budgets.map((budget) => {
      const spent = spentByCategory.get(budget.categoryId) ?? 0;
      const limit = Number(budget.limitAmount);
      const percentage = computeBudgetPercentage(spent, limit);
      return {
        budgetId: budget.id,
        categoryId: budget.categoryId,
        categoryName: budget.category?.name,
        icon: budget.category?.icon,
        color: budget.category?.color,
        limit,
        spent,
        remaining: limit - spent,
        percentage,
        status: computeBudgetStatus(percentage),
      };
    });

    return this.ok({ month, year, items });
  }

  private async spentByCategory(userId: number, month: number, year: number) {
    const { start, end } = this.monthRange(year, month);
    const rows = await this.transactionsRepository
      .createQueryBuilder('tx')
      .select('tx.category_id', 'categoryId')
      .addSelect('SUM(tx.amount)', 'spent')
      .where('tx.user_id = :userId', { userId })
      .andWhere('tx.type = :type', { type: CategoryType.EXPENSE })
      .andWhere('tx.occurred_at >= :start AND tx.occurred_at <= :end', {
        start,
        end,
      })
      .groupBy('tx.category_id')
      .getRawMany<{ categoryId: number; spent: string }>();

    return new Map(rows.map((r) => [Number(r.categoryId), parseFloat(r.spent)]));
  }

  private async requireExpenseCategory(userId: number, categoryId: number) {
    const category = await this.categoriesRepository.findOne({
      where: { id: categoryId, userId },
    });
    if (!category) {
      throw new BadRequestException('Danh mục không tồn tại hoặc không thuộc về bạn');
    }
    if (category.type !== CategoryType.EXPENSE) {
      throw new BadRequestException('Chỉ có thể đặt ngân sách cho danh mục chi tiêu');
    }
    return category;
  }

  private async findOwned(userId: number, id: number) {
    const budget = await this.budgetsRepository.findOne({
      where: { id, userId },
    });
    if (!budget) throw new NotFoundException('Không tìm thấy ngân sách');
    return budget;
  }

  private resolvePeriod(query: QueryBudgetsDto) {
    const now = new Date();
    return {
      month: query.month ?? now.getMonth() + 1,
      year: query.year ?? now.getFullYear(),
    };
  }

  private monthRange(year: number, month: number) {
    const pad = (n: number) => String(n).padStart(2, '0');
    const start = `${year}-${pad(month)}-01`;
    const lastDay = new Date(year, month, 0).getDate();
    const end = `${year}-${pad(month)}-${pad(lastDay)}`;
    return { start, end };
  }
}
