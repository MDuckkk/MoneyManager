import {
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Category } from './entities/category.entity';
import { Transaction } from '../transactions/entities/transaction.entity';
import {
  CreateCategoryDto,
  ListCategoriesQueryDto,
  UpdateCategoryDto,
} from './dto/categories.dto';
import { CategoryType } from './entities/category-type.enum';

@Injectable()
export class CategoriesService {
  constructor(
    @InjectRepository(Category)
    private readonly categoriesRepository: Repository<Category>,
    @InjectRepository(Transaction)
    private readonly transactionsRepository: Repository<Transaction>,
  ) {}

  private ok(data: unknown, message = 'Success') {
    return { success: true, message, data };
  }

  async list(userId: number, query: ListCategoriesQueryDto) {
    const categories = await this.categoriesRepository.find({
      where: { userId, ...(query.type ? { type: query.type } : {}) },
      order: { type: 'ASC', name: 'ASC' },
    });
    return this.ok(categories);
  }

  async create(userId: number, dto: CreateCategoryDto) {
    const name = dto.name.trim();
    const duplicate = await this.categoriesRepository.findOne({
      where: { userId, name, type: dto.type },
    });
    if (duplicate) {
      throw new ConflictException('Danh mục đã tồn tại');
    }

    const category = await this.categoriesRepository.save(
      this.categoriesRepository.create({
        userId,
        name,
        type: dto.type,
        icon: dto.icon ?? null,
        color: dto.color ?? null,
      }),
    );
    return this.ok(category, 'Tạo danh mục thành công');
  }

  async update(userId: number, id: number, dto: UpdateCategoryDto) {
    const category = await this.findOwned(userId, id);

    if (dto.name !== undefined) category.name = dto.name.trim();
    if (dto.type !== undefined) category.type = dto.type as CategoryType;
    if (dto.icon !== undefined) category.icon = dto.icon;
    if (dto.color !== undefined) category.color = dto.color;

    return this.ok(
      await this.categoriesRepository.save(category),
      'Cập nhật danh mục thành công',
    );
  }

  async remove(userId: number, id: number) {
    const category = await this.findOwned(userId, id);
    const usage = await this.transactionsRepository.count({
      where: { userId, categoryId: id },
    });
    if (usage > 0) {
      throw new ConflictException(
        'Không thể xóa danh mục đang có giao dịch. Hãy chuyển hoặc xóa các giao dịch trước.',
      );
    }
    await this.categoriesRepository.remove(category);
    return this.ok(null, 'Xóa danh mục thành công');
  }

  private async findOwned(userId: number, id: number) {
    const category = await this.categoriesRepository.findOne({
      where: { id, userId },
    });
    if (!category) throw new NotFoundException('Không tìm thấy danh mục');
    return category;
  }
}
