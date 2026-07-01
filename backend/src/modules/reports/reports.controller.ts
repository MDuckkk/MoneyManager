import { Controller, Get, Query } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { ReportsService } from './reports.service';
import { ByCategoryQueryDto, ReportQueryDto } from './dto/reports.dto';

@ApiTags('Reports')
@ApiBearerAuth()
@Controller('reports')
export class ReportsController {
  constructor(private readonly reportsService: ReportsService) {}

  @Get('summary')
  @ApiOperation({ summary: 'Tổng thu/chi/số dư + so sánh tháng trước' })
  summary(
    @CurrentUser('userId') userId: number,
    @Query() query: ReportQueryDto,
  ) {
    return this.reportsService.summary(userId, query);
  }

  @Get('by-category')
  @ApiOperation({ summary: 'Cơ cấu thu/chi theo danh mục (cho biểu đồ tròn)' })
  byCategory(
    @CurrentUser('userId') userId: number,
    @Query() query: ByCategoryQueryDto,
  ) {
    return this.reportsService.byCategory(userId, query);
  }
}
