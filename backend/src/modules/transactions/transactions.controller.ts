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
import { TransactionsService } from './transactions.service';
import {
  CreateTransactionDto,
  QueryTransactionsDto,
  UpdateTransactionDto,
} from './dto/transactions.dto';

@ApiTags('Transactions')
@ApiBearerAuth()
@Controller('transactions')
export class TransactionsController {
  constructor(private readonly transactionsService: TransactionsService) {}

  @Get()
  @ApiOperation({ summary: 'Danh sách giao dịch (lọc + phân trang)' })
  list(
    @CurrentUser('userId') userId: number,
    @Query() query: QueryTransactionsDto,
  ) {
    return this.transactionsService.list(userId, query);
  }

  @Post()
  @ApiOperation({ summary: 'Tạo giao dịch' })
  create(
    @CurrentUser('userId') userId: number,
    @Body() dto: CreateTransactionDto,
  ) {
    return this.transactionsService.create(userId, dto);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Chi tiết giao dịch' })
  getById(
    @CurrentUser('userId') userId: number,
    @Param('id', ParseIntPipe) id: number,
  ) {
    return this.transactionsService.getById(userId, id);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Cập nhật giao dịch' })
  update(
    @CurrentUser('userId') userId: number,
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateTransactionDto,
  ) {
    return this.transactionsService.update(userId, id, dto);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Xóa giao dịch' })
  remove(
    @CurrentUser('userId') userId: number,
    @Param('id', ParseIntPipe) id: number,
  ) {
    return this.transactionsService.remove(userId, id);
  }
}
