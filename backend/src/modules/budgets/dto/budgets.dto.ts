import { Type } from 'class-transformer';
import {
  IsInt,
  IsOptional,
  IsPositive,
  Max,
  Min,
} from 'class-validator';

export class CreateBudgetDto {
  @Type(() => Number)
  @IsInt()
  categoryId: number;

  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(12)
  month: number;

  @Type(() => Number)
  @IsInt()
  @Min(2000)
  year: number;

  @Type(() => Number)
  @IsPositive({ message: 'Hạn mức phải lớn hơn 0' })
  limitAmount: number;
}

export class UpdateBudgetDto {
  @Type(() => Number)
  @IsPositive({ message: 'Hạn mức phải lớn hơn 0' })
  limitAmount: number;
}

export class QueryBudgetsDto {
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
}
