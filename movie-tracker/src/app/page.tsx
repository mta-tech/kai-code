'use client';

import { useState, useEffect } from 'react';

interface Movie {
  id: number;
  title: string;
  year: number;
  genre: string;
  rating: number;
  image: string;
}

const MOCK_MOVIES: Movie[] = [
  { id: 1, title: "Inception", year: 2010, genre: "Sci-Fi", rating: 8.8, image: "https://images.unsplash.com/photo-1626814026160-2237a95fc5a0?q=80&w=400" },
  { id: 2, title: "The Dark Knight", year: 2008, genre: "Action", rating: 9.0, image: "https://images.unsplash.com/photo-1478720568477-152d9b164e26?q=80&w=400" },
  { id: 3, title: "Interstellar", year: 2014, genre: "Sci-Fi", rating: 8.7, image: "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=400" },
  { id: 4, title: "Parasite", year: 2019, genre: "Thriller", rating: 8.5, image: "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?q=80&w=400" },
  { id: 5, title: "The Matrix", year: 1999, genre: "Action", rating: 8.7, image: "https://images.unsplash.com/photo-1626814026160-2237a95fc5a0?q=80&w=400" },
  { id: 6, title: "Pulp Fiction", year: 1994, genre: "Crime", rating: 8.9, image: "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?q=80&w=400" },
];

export default function MovieTracker() {
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [watched, setWatched] = useState<number[]>([]);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'watchlist' | 'watched'>('all');

  // Load from localStorage
  useEffect(() => {
    const savedWatchlist = localStorage.getItem('watchlist');
    const savedWatched = localStorage.getItem('watched');
    if (savedWatchlist) setWatchlist(JSON.parse(savedWatchlist));
    if (savedWatched) setWatched(JSON.parse(savedWatched));
  }, []);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem('watchlist', JSON.stringify(watchlist));
    localStorage.setItem('watched', JSON.stringify(watched));
  }, [watchlist, watched]);

  const toggleWatchlist = (id: number) => {
    setWatchlist(prev => 
      prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
    );
  };

  const toggleWatched = (id: number) => {
    setWatched(prev => 
      prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
    );
  };

  const filteredMovies = MOCK_MOVIES.filter(movie => {
    const matchesSearch = movie.title.toLowerCase().includes(search.toLowerCase());
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'watchlist') return matchesSearch && watchlist.includes(movie.id);
    if (activeTab === 'watched') return matchesSearch && watched.includes(movie.id);
    return false;
  });

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 font-sans">
      <header className="max-w-6xl mx-auto mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
            CINE TRACKER
          </h1>
          <p className="text-gray-400">Your personal movie diary</p>
        </div>
        
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search movies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all"
          />
        </div>
      </header>

      <main className="max-w-6xl mx-auto">
        <div className="flex gap-4 mb-8 border-b border-gray-800 pb-4">
          {(['all', 'watchlist', 'watched'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2 rounded-full text-sm font-bold uppercase tracking-wider transition-all ${
                activeTab === tab 
                ? 'bg-purple-600 text-white' 
                : 'text-gray-500 hover:text-white hover:bg-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {filteredMovies.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-xl">No movies found in this collection.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {filteredMovies.map(movie => (
              <div key={movie.id} className="group relative bg-gray-900 rounded-2xl overflow-hidden border border-gray-800 hover:border-purple-500 transition-all hover:scale-[1.02]">
                <div className="aspect-[2/3] relative">
                  <img 
                    src={movie.image} 
                    alt={movie.title}
                    className="object-cover w-full h-full opacity-80 group-hover:opacity-100 transition-opacity"
                  />
                  <div className="absolute top-4 right-4 bg-black/60 backdrop-blur-md px-3 py-1 rounded-lg text-sm font-bold text-yellow-500">
                    ★ {movie.rating}
                  </div>
                </div>
                
                <div className="p-5">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-lg leading-tight">{movie.title}</h3>
                    <span className="text-xs text-gray-500 font-medium">{movie.year}</span>
                  </div>
                  <p className="text-sm text-gray-400 mb-6">{movie.genre}</p>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleWatchlist(movie.id)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
                        watchlist.includes(movie.id)
                        ? 'bg-pink-600/20 text-pink-500 border border-pink-500/50'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {watchlist.includes(movie.id) ? 'In Watchlist' : '+ Watchlist'}
                    </button>
                    <button
                      onClick={() => toggleWatched(movie.id)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
                        watched.includes(movie.id)
                        ? 'bg-green-600/20 text-green-500 border border-green-500/50'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {watched.includes(movie.id) ? 'Watched' : 'Mark Watched'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

