'use client';

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
} from 'recharts';

interface InteractiveChartsProps {
  datasetId: string;
}

interface DistributionData {
  type: string;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
  histogram?: {
    counts: number[];
    bin_edges: number[];
  };
  frequencies?: Array<{ label: string; count: number }>;
}

interface CorrelationData {
  column1: string;
  column2: string;
  correlation: number;
}

interface OutlierData {
  count: number;
  percentage: number;
  bounds: {
    lower: number;
    upper: number;
  };
}

interface VisualizationData {
  distributions?: Record<string, DistributionData>;
  correlations?: {
    strong_correlations: CorrelationData[];
  };
  outliers?: Record<string, OutlierData>;
  missing_data?: {
    total_missing: number;
    missing_percentage: number;
    columns_with_missing: Array<{
      column: string;
      missing_count: number;
      missing_percentage: number;
    }>;
  };
}

export default function InteractiveCharts({ datasetId }: InteractiveChartsProps) {
  const [data, setData] = useState<VisualizationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'distributions' | 'correlations' | 'outliers'>(
    'distributions'
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/datasets/${datasetId}/statistics`
        );

        if (!response.ok) {
          throw new Error('Erreur lors du chargement des statistiques');
        }

        const vizData = await response.json();
        setData(vizData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur inconnue');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [datasetId]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Chargement des visualisations...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null; // Graceful failure - don't show if data unavailable
  }

  // Prepare histogram data for first numeric column
  const numericDistributions = data.distributions
    ? Object.entries(data.distributions).filter(([_, d]) => d.type === 'numeric')
    : [];

  const firstNumericDist = numericDistributions.length > 0 ? numericDistributions[0] : null;
  const histogramData = firstNumericDist?.[1]?.histogram
    ? firstNumericDist[1].histogram.counts.map((count, idx) => ({
        bin: `${firstNumericDist[1].histogram!.bin_edges[idx].toFixed(1)}`,
        count,
      }))
    : [];

  // Prepare categorical frequency data
  const categoricalDistributions = data.distributions
    ? Object.entries(data.distributions).filter(([_, d]) => d.type === 'categorical')
    : [];

  const firstCategoricalDist =
    categoricalDistributions.length > 0 ? categoricalDistributions[0] : null;
  const frequencyData = firstCategoricalDist?.[1]?.frequencies?.slice(0, 10) || [];

  // Prepare correlation data for scatter plot
  const correlationData = data.correlations?.strong_correlations.map((corr, idx) => ({
    id: idx,
    name: `${corr.column1} vs ${corr.column2}`,
    x: idx,
    y: Math.abs(corr.correlation) * 100,
    correlation: corr.correlation,
  })) || [];

  // Prepare outlier data
  const outlierData = data.outliers
    ? Object.entries(data.outliers)
        .filter(([_, o]) => o.count > 0)
        .map(([col, o]) => ({
          column: col,
          count: o.count,
          percentage: o.percentage,
        }))
        .slice(0, 10)
    : [];

  return (
    <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
      <h2 className="text-2xl font-semibold text-gray-800 mb-6">
        Visualisations Interactives des Données
      </h2>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('distributions')}
          className={`px-6 py-3 font-medium transition-all border-b-2 ${
            activeTab === 'distributions'
              ? 'text-blue-600 border-blue-600'
              : 'text-gray-600 border-transparent hover:text-blue-500'
          }`}
        >
          Distributions
        </button>
        <button
          onClick={() => setActiveTab('correlations')}
          className={`px-6 py-3 font-medium transition-all border-b-2 ${
            activeTab === 'correlations'
              ? 'text-blue-600 border-blue-600'
              : 'text-gray-600 border-transparent hover:text-blue-500'
          }`}
        >
          Corrélations
        </button>
        <button
          onClick={() => setActiveTab('outliers')}
          className={`px-6 py-3 font-medium transition-all border-b-2 ${
            activeTab === 'outliers'
              ? 'text-blue-600 border-blue-600'
              : 'text-gray-600 border-transparent hover:text-blue-500'
          }`}
        >
          Valeurs Aberrantes
        </button>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'distributions' && (
          <div className="space-y-8">
            {/* Numeric Distribution */}
            {firstNumericDist && histogramData.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Distribution: {firstNumericDist[0]}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Moyenne</p>
                    <p className="text-xl font-bold text-blue-600">
                      {firstNumericDist[1].mean?.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Écart-type</p>
                    <p className="text-xl font-bold text-blue-600">
                      {firstNumericDist[1].std?.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Minimum</p>
                    <p className="text-xl font-bold text-blue-600">
                      {firstNumericDist[1].min?.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Maximum</p>
                    <p className="text-xl font-bold text-blue-600">
                      {firstNumericDist[1].max?.toFixed(2)}
                    </p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={histogramData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bin" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#3b82f6" name="Fréquence" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Categorical Distribution */}
            {firstCategoricalDist && frequencyData.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Fréquences: {firstCategoricalDist[0]}
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={frequencyData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="label" type="category" width={150} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#10b981" name="Occurrences" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {activeTab === 'correlations' && (
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Corrélations Fortes (|r| &gt; 0.7)
            </h3>
            {correlationData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" name="Paire" hide />
                    <YAxis
                      dataKey="y"
                      name="Corrélation (%)"
                      domain={[0, 100]}
                    />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
                              <p className="font-semibold">{data.name}</p>
                              <p className="text-sm text-gray-600">
                                Corrélation: {data.correlation.toFixed(3)}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Scatter data={correlationData} fill="#8b5cf6">
                      {correlationData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.correlation > 0 ? '#10b981' : '#ef4444'} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div className="mt-6 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-purple-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-purple-900 uppercase">
                          Colonne 1
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-purple-900 uppercase">
                          Colonne 2
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-purple-900 uppercase">
                          Corrélation
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {data.correlations?.strong_correlations.map((corr, idx) => (
                        <tr key={idx}>
                          <td className="px-6 py-4 text-sm text-gray-900">{corr.column1}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">{corr.column2}</td>
                          <td className="px-6 py-4 text-sm">
                            <span
                              className={`px-3 py-1 rounded-full font-medium ${
                                corr.correlation > 0
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {corr.correlation.toFixed(3)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="text-gray-600">Aucune corrélation forte détectée</p>
            )}
          </div>
        )}

        {activeTab === 'outliers' && (
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Valeurs Aberrantes Détectées (IQR Method)
            </h3>
            {outlierData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={outlierData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="column" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#f59e0b" name="Nombre d'aberrations" />
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-6 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-orange-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-orange-900 uppercase">
                          Colonne
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-orange-900 uppercase">
                          Nombre
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-orange-900 uppercase">
                          Pourcentage
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {outlierData.map((o, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-yellow-50' : ''}>
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">{o.column}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">{o.count}</td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {o.percentage.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="text-gray-600">Aucune valeur aberrante détectée</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
