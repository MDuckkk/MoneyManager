import { Type } from 'class-transformer';
import { IsEnum, IsInt, IsOptional, Max, Min } from 'class-validator';
import { CategoryType } from '../../categories/entities/category-type.enum';

export class ReportQueryDto {
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

export class ByCategoryQueryDto extends ReportQueryDto {
  @IsOptional()
  @IsEnum(CategoryType)
  type?: CategoryType;
}
