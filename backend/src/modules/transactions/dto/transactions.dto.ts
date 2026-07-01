import { PartialType } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsDateString,
  IsEnum,
  IsInt,
  IsNumberString,
  IsOptional,
  IsPositive,
  IsString,
  Max,
  MaxLength,
  Min,
} from 'class-validator';
import { CategoryType } from '../../categories/entities/category-type.enum';
import { TransactionSource } from '../entities/transaction-source.enum';

export class CreateTransactionDto {
  @Type(() => Number)
  @IsInt()
  categoryId: number;

  @Type(() => Number)
  @IsPositive({ message: 'Số tiền phải lớn hơn 0' })
  amount: number;

  @IsDateString({}, { message: 'Ngày giao dịch không hợp lệ' })
  occurredAt: string;

  @IsOptional()
  @IsString()
  @MaxLength(255)
  note?: string;

  @IsOptional()
  @IsEnum(TransactionSource)
  source?: TransactionSource;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  receiptImageUrl?: string;
}

export class UpdateTransactionDto extends PartialType(CreateTransactionDto) {}

export class QueryTransactionsDto {
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(12)
  month?: number;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(2000)
  year?: number;

  @IsOptional()
  @IsEnum(CategoryType)
  type?: CategoryType;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  categoryId?: number;

  @IsOptional()
  @IsString()
  @MaxLength(100)
  search?: string;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number = 20;
}
