import type { Language } from '@/types/index';

export const scientificUiOverrides: Record<Language, Record<string, string>> = {
  zh: {
    chart_feature_importance: '岭回归敏感度归因',
    desc_feature_importance: '标准化岭回归系数的条件关联归因；不表示因果关系，也不是 SHAP。',
    materialDurabilityForecast: '材料耐久情景投影',
    predictiveTrends: '合成趋势情景',
    resinCapacityForecast: '产能情景分析',
    sysHealthSubtitle: '系统健康与版本',
    sysHealthNoEvents: '暂无同步日志',
  },
  en: {
    chart_feature_importance: 'Ridge sensitivity attribution',
    desc_feature_importance: 'Conditional association from standardized ridge coefficients; not causality or SHAP.',
    materialDurabilityForecast: 'Material durability scenarios',
    predictiveTrends: 'Synthetic trend scenarios',
    resinCapacityForecast: 'Capacity scenario analysis',
    sysHealthSubtitle: 'System health and versioning',
    sysHealthNoEvents: 'No recent synchronization events',
  },
};
