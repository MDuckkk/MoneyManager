import { PartialType } from '@nestjs/swagger';
import {
  IsEnum,
  IsHexColor,
  IsOptional,
  IsString,
  MaxLength,
  MinLength,
} from 'class-validator';
import { CategoryType } from '../entities/category-type.enum';

export class CreateCategoryDto {
  @IsString()
  @MinLength(1)
  @MaxLength(50)
  name: string;

  @IsEnum(CategoryType, { message: 'Loại danh mục phải là INCOME hoặc EXPENSE' })
  type: CategoryType;

  @IsOptional()
  @IsString()
  @MaxLength(16)
  icon?: string;

  @IsOptional()
  @IsHexColor({ message: 'Màu phải là mã hex hợp lệ' })
  color?: string;
}

export class UpdateCategoryDto extends PartialType(CreateCategoryDto) {}

export class ListCategoriesQueryDto {
  @IsOptional()
  @IsEnum(CategoryType)
  type?: CategoryType;
}
