import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
  Unique,
  UpdateDateColumn,
} from 'typeorm';
import { User } from '../../users/entities/user.entity';
import { Category } from '../../categories/entities/category.entity';
import { numericTransformer } from '../../../common/transformers/numeric.transformer';

@Entity({ name: 'budgets' })
@Unique('uq_budget_user_category_period', ['userId', 'categoryId', 'month', 'year'])
@Index('idx_budget_user_period', ['userId', 'year', 'month'])
export class Budget {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ name: 'user_id', type: 'int' })
  userId: number;

  @ManyToOne(() => User, (user) => user.budgets, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User;

  @Column({ name: 'category_id', type: 'int' })
  categoryId: number;

  @ManyToOne(() => Category, (category) => category.budgets, {
    onDelete: 'CASCADE',
  })
  @JoinColumn({ name: 'category_id' })
  category: Category;

  @Column({ type: 'smallint' })
  month: number;

  @Column({ type: 'int' })
  year: number;

  @Column({
    name: 'limit_amount',
    type: 'decimal',
    precision: 14,
    scale: 2,
    transformer: numericTransformer,
  })
  limitAmount: number;

  @CreateDateColumn({ name: 'created_at', type: 'timestamptz' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at', type: 'timestamptz' })
  updatedAt: Date;
}
