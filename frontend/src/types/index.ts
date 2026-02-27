export interface Option {
  id: number;
  name: string;
  price: number;
  description: string;
  active: boolean;
}

export interface Machine {
  id: number;
  code: string;
  name: string;
  price: number;
  category: string;
  description: string;
  active: boolean;
  model_name?: string;
  product_title?: string;
  price_currency?: string;
  options?: Option[];
  availableOptions?: Option[];
}

export interface QuotationForm {
  clientName: string;
  clientCuit: string;
  clientPhone: string;
  clientAddress: string;
  clientEmail: string;
  clientCompany: string;
  notes: string;
}
