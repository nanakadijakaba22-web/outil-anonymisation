"use client";

import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function Header() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleProfile = () => {
    router.push('/profile');
  };

  if (!user) {
    return null;
  }

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-8 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-lg">
                {user.email.charAt(0).toUpperCase()}
              </div>
              <div className="ml-3">
                <p className="text-sm font-semibold text-gray-900">
                  {user.full_name || user.email}
                </p>
                <p className="text-xs text-gray-500">{user.email}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3 mr-48">
            <button
              onClick={handleProfile}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              Profil
            </button>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
            >
              Se déconnecter
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
