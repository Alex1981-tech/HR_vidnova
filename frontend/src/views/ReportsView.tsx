import type { ReactElement } from 'react';
import { useLocation } from 'react-router-dom';

import { ReportsIndex } from './reports/ReportsIndex';
import { HeadcountReportView } from './reports/HeadcountReportView';
import { TurnoverReportView } from './reports/TurnoverReportView';
import { TenureReportView } from './reports/TenureReportView';

// Routes /reports and /reports/<key>. Index list when no key (or unknown key);
// a dedicated analytics view when the key is implemented.
const REPORT_VIEWS: Record<string, () => ReactElement> = {
  headcount: HeadcountReportView,
  turnover: TurnoverReportView,
  tenure: TenureReportView,
};

export function ReportsView() {
  const location = useLocation();
  const [, , key] = location.pathname.split('/');
  const View = key ? REPORT_VIEWS[key] : undefined;
  return View ? <View /> : <ReportsIndex />;
}
