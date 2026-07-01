import { ValueTransformer } from 'typeorm';

/**
 * TypeORM trả cột `decimal` của Postgres về dạng string để giữ độ chính xác.
 * Transformer này chuyển sang number khi đọc ra (giá trị tiền tệ chỉ tới 2 chữ số thập phân,
 * nằm trong khoảng an toàn của Number nên không mất độ chính xác).
 */
export class NumericTransformer implements ValueTransformer {
  to(value: number | null): number | null {
    return value;
  }

  from(value: string | null): number | null {
    return value === null || value === undefined ? null : parseFloat(value);
  }
}

export const numericTransformer = new NumericTransformer();
