import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Link2, TrendingUp, Database, Zap, Copy, ExternalLink, Trash2, BarChart3 } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
// const BACKEND_URL = "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

const Home = () => {
  const [url, setUrl] = useState("");
  const [customAlias, setCustomAlias] = useState("");
  const [shortenedUrl, setShortenedUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [urls, setUrls] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedStats, setSelectedStats] = useState(null);

  useEffect(() => {
    fetchUrls();
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUrls = async () => {
    try {
      const response = await axios.get(`${API}/urls?limit=50`);
      setUrls(response.data);
    } catch (error) {
      console.error("Error fetching URLs:", error);
    }
  };

  const fetchMetrics = async () => {
    try {
      const response = await axios.get(`${API}/metrics`);
      setMetrics(response.data);
    } catch (error) {
      console.error("Error fetching metrics:", error);
    }
  };

  const handleShorten = async (e) => {
    e.preventDefault();
    if (!url.trim()) {
      toast.error("Please enter a URL");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/shorten`, {
        url: url.trim(),
        custom_alias: customAlias.trim() || null
      });
      
      const shortUrl = `${BACKEND_URL}/api/expand/${response.data.short_code}`;
      setShortenedUrl(shortUrl);
      toast.success("URL shortened successfully!");
      setUrl("");
      setCustomAlias("");
      fetchUrls();
      fetchMetrics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to shorten URL");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  const deleteUrl = async (shortCode) => {
    try {
      await axios.delete(`${API}/urls/${shortCode}`);
      toast.success("URL deleted successfully");
      fetchUrls();
      fetchMetrics();
    } catch (error) {
      toast.error("Failed to delete URL");
    }
  };

  const viewStats = async (shortCode) => {
    try {
      const response = await axios.get(`${API}/stats/${shortCode}`);
      setSelectedStats(response.data);
    } catch (error) {
      toast.error("Failed to fetch stats");
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Distributed URL Shortener</h1>
          <p className="text-slate-600">High-performance URL shortening with LRU caching, rate limiting, and real-time analytics</p>
        </div>

        {/* System Metrics */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <Card data-testid="total-urls-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-600">Total URLs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Link2 className="h-5 w-5 text-blue-600" />
                  <span className="text-2xl font-bold text-slate-900">{metrics.total_urls}</span>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="total-clicks-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-600">Total Clicks</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  <span className="text-2xl font-bold text-slate-900">{metrics.total_clicks}</span>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="cache-hit-rate-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-600">Cache Hit Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-amber-600" />
                  <span className="text-2xl font-bold text-slate-900">{metrics.cache_stats.hit_rate}%</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {metrics.cache_stats.size}/{metrics.cache_stats.capacity} cached
                </p>
              </CardContent>
            </Card>

            <Card data-testid="recent-activity-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-600">Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-purple-600" />
                  <span className="text-2xl font-bold text-slate-900">{metrics.recent_clicks}</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">clicks in last hour</p>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="shorten" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="shorten" data-testid="shorten-tab">Shorten URL</TabsTrigger>
            <TabsTrigger value="urls" data-testid="urls-tab">URL List</TabsTrigger>
            <TabsTrigger value="analytics" data-testid="analytics-tab">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="shorten" data-testid="shorten-content">
            <Card>
              <CardHeader>
                <CardTitle>Create Short URL</CardTitle>
                <CardDescription>Enter a long URL to generate a short, shareable link</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleShorten} className="space-y-4">
                  <div>
                    <Input
                      data-testid="url-input"
                      type="text"
                      placeholder="https://example.com/very-long-url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <Input
                      data-testid="custom-alias-input"
                      type="text"
                      placeholder="Custom alias (optional)"
                      value={customAlias}
                      onChange={(e) => setCustomAlias(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <Button 
                    data-testid="shorten-button"
                    type="submit" 
                    disabled={loading}
                    className="w-full"
                  >
                    {loading ? "Shortening..." : "Shorten URL"}
                  </Button>
                </form>

                {shortenedUrl && (
                  <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg" data-testid="result-container">
                    <p className="text-sm text-slate-600 mb-2">Your shortened URL:</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 p-2 bg-white border rounded text-sm font-mono text-slate-900">
                        {shortenedUrl}
                      </code>
                      <Button
                        data-testid="copy-button"
                        size="sm"
                        variant="outline"
                        onClick={() => copyToClipboard(shortenedUrl)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        data-testid="open-button"
                        size="sm"
                        variant="outline"
                        onClick={() => window.open(shortenedUrl, '_blank')}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="urls" data-testid="urls-content">
            <Card>
              <CardHeader>
                <CardTitle>Shortened URLs</CardTitle>
                <CardDescription>Manage all your shortened URLs</CardDescription>
              </CardHeader>
              <CardContent>
                {urls.length === 0 ? (
                  <p className="text-center text-slate-500 py-8">No URLs yet. Create your first one!</p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Short Code</TableHead>
                          <TableHead>Original URL</TableHead>
                          <TableHead>Clicks</TableHead>
                          <TableHead>Created</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {urls.map((urlItem) => (
                          <TableRow key={urlItem.short_code} data-testid={`url-row-${urlItem.short_code}`}>
                            <TableCell>
                              <code className="text-sm font-mono text-blue-600">{urlItem.short_code}</code>
                              {urlItem.custom_alias && <Badge className="ml-2" variant="secondary">Custom</Badge>}
                            </TableCell>
                            <TableCell className="max-w-xs truncate" title={urlItem.original_url}>
                              {urlItem.original_url}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{urlItem.clicks}</Badge>
                            </TableCell>
                            <TableCell className="text-sm text-slate-600">
                              {formatDate(urlItem.created_at)}
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-2">
                                <Button
                                  data-testid={`stats-button-${urlItem.short_code}`}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => viewStats(urlItem.short_code)}
                                >
                                  <BarChart3 className="h-4 w-4" />
                                </Button>
                                <Button
                                  data-testid={`delete-button-${urlItem.short_code}`}
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => deleteUrl(urlItem.short_code)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" data-testid="analytics-content">
            <div className="grid gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Top Performing URLs</CardTitle>
                  <CardDescription>Most clicked shortened URLs</CardDescription>
                </CardHeader>
                <CardContent>
                  {metrics?.top_urls && metrics.top_urls.length > 0 ? (
                    <div className="space-y-3">
                      {metrics.top_urls.map((item, index) => (
                        <div key={item.short_code} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-bold text-slate-400">#{index + 1}</span>
                            <div>
                              <code className="text-sm font-mono text-blue-600">{item.short_code}</code>
                              <p className="text-xs text-slate-600 truncate max-w-md">{item.original_url}</p>
                            </div>
                          </div>
                          <Badge variant="secondary" className="text-base">{item.clicks} clicks</Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-8">No data available yet</p>
                  )}
                </CardContent>
              </Card>

              {selectedStats && (
                <Card data-testid="selected-stats-card">
                  <CardHeader>
                    <CardTitle>Detailed Statistics: {selectedStats.short_code}</CardTitle>
                    <CardDescription>{selectedStats.original_url}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-sm text-slate-600">Total Clicks</p>
                          <p className="text-2xl font-bold text-slate-900">{selectedStats.clicks}</p>
                        </div>
                        <div>
                          <p className="text-sm text-slate-600">Created</p>
                          <p className="text-sm font-medium text-slate-900">{formatDate(selectedStats.created_at)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-slate-600">Last Accessed</p>
                          <p className="text-sm font-medium text-slate-900">
                            {selectedStats.last_accessed ? formatDate(selectedStats.last_accessed) : 'Never'}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-slate-600">Recent Events</p>
                          <p className="text-2xl font-bold text-slate-900">{selectedStats.click_history?.length || 0}</p>
                        </div>
                      </div>

                      {selectedStats.click_history && selectedStats.click_history.length > 0 && (
                        <div>
                          <h4 className="font-medium mb-2">Recent Click Events</h4>
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {selectedStats.click_history.map((click, index) => (
                              <div key={index} className="text-xs p-2 bg-slate-50 rounded border">
                                <p className="font-mono text-slate-600">{formatDate(click.timestamp)}</p>
                                {click.user_agent && (
                                  <p className="text-slate-500 truncate">User Agent: {click.user_agent}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Technical Features Footer */}
        <div className="mt-8 p-6 bg-white border rounded-lg" data-testid="architecture-features">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">System Architecture Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-slate-900 mb-2">Caching Strategy</h4>
              <ul className="space-y-1 text-slate-600">
                <li>• LRU in-memory cache with O(1) operations</li>
                <li>• Write-through and read-through patterns</li>
                <li>• Cache warming on URL creation</li>
                <li>• Real-time cache hit rate monitoring</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-slate-900 mb-2">Distributed Systems</h4>
              <ul className="space-y-1 text-slate-600">
                <li>• Base62 encoding for collision-resistant IDs</li>
                <li>• Counter-based collision handling</li>
                <li>• Horizontal scaling ready architecture</li>
                <li>• Database indexing for query optimization</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-slate-900 mb-2">Performance</h4>
              <ul className="space-y-1 text-slate-600">
                <li>• Token bucket rate limiting (100 req/min)</li>
                <li>• Async operations for non-blocking I/O</li>
                <li>• Optimized MongoDB queries with projections</li>
                <li>• Sub-millisecond cache response times</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-slate-900 mb-2">Analytics & Monitoring</h4>
              <ul className="space-y-1 text-slate-600">
                <li>• Real-time click tracking and analytics</li>
                <li>• Aggregation pipelines for insights</li>
                <li>• Time-series data for trend analysis</li>
                <li>• System-wide performance metrics</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      <Toaster position="top-right" />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;