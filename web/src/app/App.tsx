import { Route, Routes } from "react-router-dom";

import { CustomerLayout } from "../features/customer/CustomerLayout";
import { OverviewPage } from "../features/overview/OverviewPage";
import { PortfolioPage } from "../features/portfolio/PortfolioPage";
import { ProcessPage } from "../features/process/ProcessPage";
import { ReadinessPage } from "../features/readiness/ReadinessPage";
import { TenderPage } from "../features/tenders/TenderPage";
import { TendersPage } from "../features/tenders/TendersPage";
import { ValuePage } from "../features/value/ValuePage";
import { EmptyState } from "../shared/ui";
import { Shell } from "./Shell";

function NotFound() {
  return (
    <EmptyState title="There is nothing at this address">
      Pick a customer on the left, or go back to all customers.
    </EmptyState>
  );
}

export function AppRoutes() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<PortfolioPage />} />
        <Route path="/c/:cid" element={<CustomerLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="process" element={<ProcessPage />} />
          <Route path="tenders" element={<TendersPage />} />
          <Route path="tenders/:tid" element={<TenderPage />} />
          <Route path="readiness" element={<ReadinessPage />} />
          <Route path="value" element={<ValuePage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Shell>
  );
}
