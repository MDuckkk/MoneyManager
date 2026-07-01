import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Transaction } from './entities/transaction.entity';
import { Category } from '../categories/entities/category.entity';
import {
  CreateTransactionDto,
  QueryTransactionsDto,
  UpdateTransactionDto,
} from './dto/transactions.dto';

@Injectable()
export class TransactionsService {
  constructor(
    @InjectRepository(Transaction)
    private readonly transactionsRepository: Repository<Transaction>,
    @InjectRepository(Category)
    private readonly categoriesRepository: Repository<Category>,
  ) {}

  private ok(data: unknown, message = 'Success') {
    return { success: true, message, data };
  }

  async create(userId: number, dto: CreateTransactionDto) {
    const category = await this.requireCategory(userId, dto.categoryId);

    const transaction = await this.transactionsRepository.save(
      this.transactionsRepository.create({
        userId,
        categoryId: category.id,
        type: category.type,
        amount: dto.amount,
        note: dto.note?.trim() || null,
        occurredAt: dto.occurredAt.slice(0, 10),
        source: dto.source,
        receiptImageUrl: dto.receiptImageUrl || null,
      }),
    );

    return this.ok(
      await this.findWithCategory(userId, transaction.id),
      'Tạo giao dịch thành công',
    );
  }

  async list(userId: number, query: QueryTransactionsDto) {
    const page = query.page ?? 1;
    const limit = query.limit ?? 20;

    const qb = this.transactionsRepository
      .createQueryBuilder('tx')
      .leftJoinAndSelect('tx.category', 'category')
      .where('tx.user_id = :userId', { userId });

    if (query.type) qb.andWhere('tx.type = :type', { type: query.type });
    if (query.categoryId)
      qb.andWhere('tx.category_id = :categoryId', {
        categoryId: query.categoryId,
      });
    if (query.search)
      qb.andWhere('tx.note ILIKE :search', { search: `%${query.search}%` });

    if (query.year && query.month) {
      const { start, end } = this.monthRange(query.year, query.month);
      qb.andWhere('tx.occurred_at >= :start AND tx.occurred_at <= :end', {
        start,
        end,
      });
    } else if (query.year) {
      qb.andWhere('EXTRACT(YEAR FROM tx.occurred_at) = :year', {
        year: query.year,
      });
    }

    qb.orderBy('tx.occurredAt', 'DESC')
      .addOrderBy('tx.id', 'DESC')
      .skip((page - 1) * limit)
      .take(limit);

    const [rows, total] = await qb.getManyAndCount();

    return {
      success: true,
      message: 'Success',
      data: rows,
      meta: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit) || 1,
      },
    };
  }

  async getById(userId: number, id: number) {
    return this.ok(await this.findWithCategory(userId, id));
  }

  async update(userId: number, id: number, dto: UpdateTransactionDto) {
    const transaction = await this.findOwned(userId, id);

    if (dto.categoryId !== undefined) {
      const category = await this.requireCategory(userId, dto.categoryId);
      transaction.categoryId = category.id;
      transaction.type = category.type;
    }
    if (dto.amount !== undefined) transaction.amount = dto.amount;
    if (dto.note !== undefined) transaction.note = dto.note?.trim() || null;
    if (dto.occurredAt !== undefined)
      transaction.occurredAt = dto.occurredAt.slice(0, 10);
    if (dto.receiptImageUrl !== undefined)
      transaction.receiptImageUrl = dto.receiptImageUrl || null;

    await this.transactionsRepository.save(transaction);
    return this.ok(
      await this.findWithCategory(userId, id),
      'Cập nhật giao dịch thành công',
    );
  }

  async remove(userId: number, id: number) {
    const transaction = await this.findOwned(userId, id);
    await this.transactionsRepository.remove(transaction);
    return this.ok(null, 'Xóa giao dịch thành công');
  }

  private async requireCategory(userId: number, categoryId: number) {
    const category = await this.categoriesRepository.findOne({
      where: { id: categoryId, userId },
    });
    if (!category) {
      throw new BadRequestException('Danh mục không tồn tại hoặc không thuộc về bạn');
    }
    return category;
  }

  private async findOwned(userId: number, id: number) {
    const transaction = await this.transactionsRepository.findOne({
      where: { id, userId },
    });
    if (!transaction) throw new NotFoundException('Không tìm thấy giao dịch');
    return transaction;
  }

  private async findWithCategory(userId: number, id: number) {
    const transaction = await this.transactionsRepository.findOne({
      where: { id, userId },
      relations: { category: true },
    });
    if (!transaction) throw new NotFoundException('Không tìm thấy giao dịch');
    return transaction;
  }

  private monthRange(year: number, month: number) {
    const pad = (n: number) => String(n).padStart(2, '0');
    const start = `${year}-${pad(month)}-01`;
    const lastDay = new Date(year, month, 0).getDate();
    const end = `${year}-${pad(month)}-${pad(lastDay)}`;
    return { start, end };
  }
}
