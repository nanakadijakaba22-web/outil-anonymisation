'use client';

import { DatasetPreview } from '@/lib/api';

interface DataPreviewTableProps {
  preview: DatasetPreview;
  isLoading?: boolean;
}

export default function DataPreviewTable({ preview, isLoading = false }: DataPreviewTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <svg
            className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          <p className="text-gray-600">Chargement de la prévisualisation...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-600">Colonnes</p>
            <p className="text-2xl font-bold text-gray-900">{preview.columns.length}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Lignes totales</p>
            <p className="text-2xl font-bold text-gray-900">{preview.total_rows.toLocaleString()}</p>
          </div>
          <div className="col-span-2 md:col-span-1">
            <p className="text-sm text-gray-600">Lignes affichées</p>
            <p className="text-2xl font-bold text-gray-900">{preview.sample_rows.length}</p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {preview.columns.map((column) => (
                  <th
                    key={`col-${column}`}
                    scope="col"
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {preview.sample_rows.map((row, rowIndex) => (
                <tr key={`row-${rowIndex}`} className="hover:bg-gray-50">
                  {preview.columns.map((column) => (
                    <td
                      key={`${rowIndex}-${column}`}
                      className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      {row[column] !== null && row[column] !== undefined
                        ? String(row[column])
                        : <span className="text-gray-400 italic">null</span>
                      }
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Preview Notice */}
      {preview.sample_rows.length < preview.total_rows && (
        <p className="text-sm text-gray-500 text-center">
          Affichage des {preview.sample_rows.length} premières lignes sur {preview.total_rows.toLocaleString()} au total
        </p>
      )}
    </div>
  );
}
