import {
  computeBudgetPercentage,
  computeBudgetStatus,
} from './budget-status.util';

describe('budget-status util', () => {
  describe('computeBudgetStatus', () => {
    it('trả SAFE khi dưới 80%', () => {
      expect(computeBudgetStatus(0)).toBe('SAFE');
      expect(computeBudgetStatus(79)).toBe('SAFE');
    });

    it('trả WARNING khi 80%–100%', () => {
      expect(computeBudgetStatus(80)).toBe('WARNING');
      expect(computeBudgetStatus(100)).toBe('WARNING');
    });

    it('trả EXCEEDED khi vượt 100%', () => {
      expect(computeBudgetStatus(101)).toBe('EXCEEDED');
      expect(computeBudgetStatus(250)).toBe('EXCEEDED');
    });
  });

  describe('computeBudgetPercentage', () => {
    it('tính đúng phần trăm đã dùng', () => {
      expect(computeBudgetPercentage(2400000, 3000000)).toBe(80);
      expect(computeBudgetPercentage(1500000, 3000000)).toBe(50);
    });

    it('trả 0 khi hạn mức <= 0 (tránh chia cho 0)', () => {
      expect(computeBudgetPercentage(1000, 0)).toBe(0);
    });
  });
});
