import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { User } from '../../users/entities/user.entity';
import { Category } from '../../categories/entities/category.entity';
import { CategoryType } from '../../categories/entities/category-type.enum';
import { numericTransformer } from '../../../common/transformers/numeric.transformer';
import { TransactionSource } from './transaction-source.enum';

@Entity({ name: 'transactions' })
@Index('idx_tx_user_occurred', ['userId', 'occurredAt'])
@Index('idx_tx_user_category', ['userId', 'categoryId'])
export class Transaction {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ name: 'user_id', type: 'int' })
  userId: number;

  @ManyToOne(() => User, (user) => user.transactions, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User;

  @Column({ name: 'category_id', type: 'int' })
  categoryId: number;

  @ManyToOne(() => Category, (category) => category.transactions, {
    onDelete: 'RESTRICT',
  })
  @JoinColumn({ name: 'category_id' })
  category: Category;

  // Denormalize loại từ Category để truy vấn/báo cáo nhanh, không cần join.
  @Column({ type: 'enum', enum: CategoryType })
  type: CategoryType;

  @Column({
    type: 'decimal',
    precision: 14,
    scale: 2,
    transformer: numericTransformer,
  })
  amount: number;

  @Column({ type: 'varchar', length: 255, nullable: true })
  note: string | null;

  @Index()
  @Column({ name: 'occurred_at', type: 'date' })
  occurredAt: string;

  @Column({
    type: 'enum',
    enum: TransactionSource,
    default: TransactionSource.MANUAL,
  })
  source: TransactionSource;

  @Column({ name: 'receipt_image_url', type: 'varchar', length: 500, nullable: true })
  receiptImageUrl: string | null;

  @CreateDateColumn({ name: 'created_at', type: 'timestamptz' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at', type: 'timestamptz' })
  updatedAt: Date;
}
