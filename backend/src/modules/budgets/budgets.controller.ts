import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseIntPipe,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { BudgetsService } from './budgets.service';
import {
  CreateBudgetDto,
  QueryBudgetsDto,
  UpdateBudgetDto,
} from './dto/budgets.dto';

@ApiTags('Budgets')
@ApiBearerAuth()
@Controller('budgets')
export class BudgetsController {
  constructor(private readonly budgetsService: BudgetsService) {}

  @Get()
  @ApiOperation({ summary: 'Danh sách ngân sách của tháng' })
  list(
    @CurrentUser('userId') userId: number,
    @Query() query: QueryBudgetsDto,
  ) {
    return this.budgetsService.list(userId, query);
  }

  @Get('status')
  @ApiOperation({ summary: 'Tiến độ ngân sách (đã chi vs hạn mức)' })
  status(
    @CurrentUser('userId') userId: number,
    @Query() query: QueryBudgetsDto,
  ) {
    return this.budgetsService.status(userId, query);
  }

  @Post()
  @ApiOperation({ summary: 'Tạo ngân sách' })
  create(@CurrentUser('userId') userId: number, @Body() dto: CreateBudgetDto) {
    return this.budgetsService.create(userId, dto);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Cập nhật hạn mức ngân sách' })
  update(
    @CurrentUser('userId') userId: number,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateBudgetDto,
  ) {
    return this.budgetsService.update(userId, id, dto);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Xóa ngân sách' })
  remove(
    @CurrentUser('userId') userId: number,
    @Param('id', ParseIntPipe) id: number,
  ) {
    return this.budgetsService.remove(userId, id);
  }
}
