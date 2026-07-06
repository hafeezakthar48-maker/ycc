export type MoneyValue = number | string;

export interface PayrollEmployeeInput {
  employee_id: string;
  employee_name: string;
  department: string;
  base_salary: MoneyValue;
  bonus?: MoneyValue;
  allowance?: MoneyValue;
  social_security_base: MoneyValue;
  housing_fund_base: MoneyValue;
  special_additional_deduction?: MoneyValue;
  other_deduction?: MoneyValue;
}

export interface PayrollCalculateRequest {
  account_set_id?: string;
  period: string;
  operator?: string;
  employees: PayrollEmployeeInput[];
}

export interface PayrollEmployeeResult {
  employee_id: string;
  employee_name: string;
  department: string;
  gross_pay: MoneyValue;
  employee_social_security: MoneyValue;
  employer_social_security: MoneyValue;
  employee_housing_fund: MoneyValue;
  employer_housing_fund: MoneyValue;
  special_additional_deduction: MoneyValue;
  taxable_income: MoneyValue;
  tax_rate: MoneyValue;
  quick_deduction: MoneyValue;
  individual_income_tax: MoneyValue;
  other_deduction: MoneyValue;
  net_pay: MoneyValue;
  employer_cost: MoneyValue;
}

export interface PayrollSummary {
  employee_count: number;
  gross_pay_total: MoneyValue;
  employee_social_security_total: MoneyValue;
  employer_social_security_total: MoneyValue;
  employee_housing_fund_total: MoneyValue;
  employer_housing_fund_total: MoneyValue;
  individual_income_tax_total: MoneyValue;
  net_pay_total: MoneyValue;
  employer_cost_total: MoneyValue;
  average_net_pay: MoneyValue;
}

export interface PayrollDepartmentSummary {
  department: string;
  employee_count: number;
  gross_pay_total: MoneyValue;
  net_pay_total: MoneyValue;
  employer_cost_total: MoneyValue;
}

export interface PayrollCalculationResponse {
  account_set_id: string;
  period: string;
  operator: string;
  summary: PayrollSummary;
  employees: PayrollEmployeeResult[];
  department_analysis: PayrollDepartmentSummary[];
}
