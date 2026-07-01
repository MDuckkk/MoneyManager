import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

type ExceptionPayload = {
  message?: string | string[];
  errors?: unknown;
  code?: string;
};

/**
 * Chuẩn hóa mọi lỗi về envelope thống nhất:
 * { success, message, code?, statusCode, data, path, timestamp }
 */
@Catch()
export class HttpExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(HttpExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message: string | string[] = 'Internal server error';
    let data: unknown = null;

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else if (typeof exceptionResponse === 'object') {
        const payload = exceptionResponse as ExceptionPayload;
        message = payload.message || exception.message;
        data = payload.errors || null;

        response.status(status).json({
          success: false,
          message: this.normalizeMessage(message),
          code: payload.code,
          statusCode: status,
          data,
          path: request.url,
          timestamp: new Date().toISOString(),
        });
        return;
      }
    } else if (exception instanceof Error) {
      message = exception.message;
      this.logger.error(
        `Unhandled error: ${exception.message}`,
        exception.stack,
      );
    }

    response.status(status).json({
      success: false,
      message: this.normalizeMessage(message),
      statusCode: status,
      data,
      path: request.url,
      timestamp: new Date().toISOString(),
    });
  }

  private normalizeMessage(message: string | string[]) {
    return Array.isArray(message) ? (message[0] ?? 'Error') : message;
  }
}
