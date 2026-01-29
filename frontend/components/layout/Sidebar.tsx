'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { 
  Videocam, 
  DirectionsCar, 
  History, 
  Assessment, 
  Settings, 
  Logout, 
  ExpandMore, 
  ChevronRight,
  AccountCircle,
  Construction,
  LiveTv,
  Tune,
  Assignment
} from '@mui/icons-material'

interface MenuItem {
  title: string
  href?: string
  icon: React.ElementType
  subItems?: { title: string; href: string; tag?: string }[]
  key?: string // Unique key for state management
}

// Static Items
const STATIC_MENU_ITEMS: MenuItem[] = [
  {
    title: 'Danh sách xe đăng ký',
    icon: DirectionsCar,
    href: '/vehicles'
  },
  {
    title: 'Danh sách Camera',
    href: '/cameras',
    icon: Videocam 
  },
  {
    title: 'Lịch sử ra vào',
    href: '/history',
    icon: History
  },
  {
    title: 'Báo cáo',
    href: '/reports',
    icon: Assessment
  },
  {
    title: 'Nhật ký',
    href: '/logs',
    icon: Assignment
  }
]

export default function Sidebar() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const [openMenus, setOpenMenus] = useState<string[]>(['Giám sát trực tuyến'])
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  // Resizable Sidebar State
  const [sidebarWidth, setSidebarWidth] = useState(256) // Default 256px (w-64)
  const [isResizing, setIsResizing] = useState(false)
  
  // Dynamic Locations State
  const [monitorSubItems, setMonitorSubItems] = useState<{ title: string; href: string; tag?: string }[]>([])
  const [userData, setUserData] = useState<{username: string, role: string, full_name?: string} | null>(null)

  // Drag handlers
  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }

  const stopResizing = () => {
    setIsResizing(false)
  }

  const resizeSidebar = (e: MouseEvent) => {
    if (isResizing && !isCollapsed) {
      const newWidth = e.clientX
      if (newWidth >= 250 && newWidth <= 400) {
        setSidebarWidth(newWidth)
      }
    }
  }

  useEffect(() => {
    if (isResizing) {
        window.addEventListener('mousemove', resizeSidebar)
        window.addEventListener('mouseup', stopResizing)
        document.body.style.cursor = 'col-resize'
        document.body.style.userSelect = 'none'
    } else {
        window.removeEventListener('mousemove', resizeSidebar)
        window.removeEventListener('mouseup', stopResizing)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
    }
    return () => {
        window.removeEventListener('mousemove', resizeSidebar)
        window.removeEventListener('mouseup', stopResizing)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
    }
  }, [isResizing])

  // Load user data
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
        try {
            setUserData(JSON.parse(savedUser));
        } catch (e) {}
    }
    const savedWidth = localStorage.getItem('sidebar_width');
    if (savedWidth) {
        const w = parseInt(savedWidth)
        if (w >= 250 && w <= 400) setSidebarWidth(w)
    }
  }, []);

  useEffect(() => {
    if (!isCollapsed) {
        localStorage.setItem('sidebar_width', sidebarWidth.toString());
    }
  }, [sidebarWidth, isCollapsed]);

  // Load Locations for Sidebar
  useEffect(() => {
    // 1. Initial Load
    const loadLocations = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const res = await fetch('/api/cameras/locations', {
              headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
                const locs: Array<{id: string | number, name: string, tag?: string}> = await res.json()
                const items = locs.map(loc => ({
                    title: loc.name, 
                    href: `/monitor?gate=${encodeURIComponent(loc.name)}`,
                    tag: loc.tag
                }))
                setMonitorSubItems(items)
            }
        } catch (e) {
            console.error("Failed to sync sidebar locations", e)
        }
    }
    
    loadLocations()

    // 2. Listen for custom event 'cammana_locations_updated'
    const handleSync = () => loadLocations()
    window.addEventListener('cammana_locations_updated', handleSync)
    
    // 3. Fallback interval for other changes
    const interval = setInterval(loadLocations, 30000)
    
    return () => {
      clearInterval(interval)
      window.removeEventListener('cammana_locations_updated', handleSync)
    }
  }, [])

  const fullMenu: MenuItem[] = [
    {
        title: 'Giám sát trực tuyến',
        icon: LiveTv,
        subItems: monitorSubItems,
        href: '/monitor'
    },
    ...STATIC_MENU_ITEMS.filter(item => {
        // High-level filtering
        if (item.title === 'Danh sách Camera') return true; // Everyone can view the list
        if (item.title === 'Danh sách xe đăng ký' && userData?.role !== 'admin' && !(userData as any)?.can_add_vehicles) return false;
        return true;
    })
  ]

  const handleMainClick = (item: MenuItem) => {
    // If collapsed, expand sidebar first
    if (isCollapsed) {
        setIsCollapsed(false)
        if (item.subItems && !openMenus.includes(item.title)) {
            setOpenMenus(prev => [...prev, item.title])
        }
        if (item.href) router.push(item.href)
        return
    }

    // If expanded, navigate if href exists
    if (item.href) {
        router.push(item.href)
    } else {
        // Fallback: toggle if no href (act as folder)
        toggleSubmenu(item.title)
    }
  }

  const toggleSubmenu = (title: string) => {
    setOpenMenus(prev => 
      prev.includes(title) 
        ? prev.filter(t => t !== title)
        : [...prev, title]
    )
  }

  return (
    <aside 
        style={{ width: isCollapsed ? 64 : sidebarWidth }}
        className={`h-full bg-sidebar border-r border-sidebar-border flex flex-col shrink-0 overflow-x-hidden relative group/sidebar
          ${!isResizing ? 'transition-[width] duration-300' : 'select-none'}
        `}
    >
      {/* Resize Handle */}
      {!isCollapsed && (
        <div 
          onMouseDown={startResizing}
          className={`absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-primary/40 transition-colors z-50 ${isResizing ? 'bg-primary' : ''}`}
        />
      )}
      {/* Branding */}
      <div className={`h-16 flex items-center border-b border-sidebar-border relative ${isCollapsed ? 'justify-center px-0' : 'justify-between pl-6 pr-2'}`}>
        {!isCollapsed && (
            <div className="flex items-center">
                <Construction className="text-primary mr-3" />
                <span className="font-bold text-lg text-primary tracking-tight whitespace-nowrap">CamMana</span>
            </div>
        )}
        
        {/* Toggle Button */}
        <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={`text-muted-foreground hover:text-primary transition-colors ${isCollapsed ? '' : 'p-1'}`}
            title={isCollapsed ? "Mở rộng" : "Thu gọn"}
        >
            {isCollapsed ? <Construction className="text-primary" /> : <div className="p-1 rounded hover:bg-sidebar-accent"><ChevronRight className="rotate-180" /></div>}
        </button>
      </div>

      {/* Navigation */}
      <nav className={`flex-1 overflow-y-auto overflow-x-hidden py-4 space-y-1 ${isCollapsed ? 'px-2' : 'px-3'} scrollbar-hide`}>
        {fullMenu.map((item) => (
          <div key={item.title}>
            {item.subItems ? (
              // Dropdown Menu
              <div>
                <div 
                  className={`w-full flex items-center relative rounded-md text-sm font-medium transition-colors mb-1 group
                    ${(pathname === item.href) || openMenus.includes(item.title) ? 'text-sidebar-foreground' : 'text-muted-foreground hover:text-sidebar-accent-foreground'}
                    ${isCollapsed ? 'justify-center' : 'justify-between'}
                    hover:bg-sidebar-accent
                  `}
                >
                    {/* Main Click Area */}
                    <div 
                        onClick={() => handleMainClick(item)}
                        className={`flex-1 flex items-center gap-3 py-2 cursor-pointer ${isCollapsed ? 'justify-center px-0' : 'px-3'}`}
                        title={isCollapsed ? item.title : undefined}
                    >
                        <item.icon fontSize="small" className="shrink-0 text-[#f59e0b]" />
                        {!isCollapsed && <span className="whitespace-nowrap">{item.title}</span>}
                    </div>

                    {/* Toggle Arrow (Only visible when expanded) */}
                    {!isCollapsed && (
                        <div 
                            onClick={(e) => {
                                e.stopPropagation();
                                toggleSubmenu(item.title);
                            }}
                            className="p-2 cursor-pointer hover:bg-sidebar-accent/80 rounded-r-md"
                        >
                            {openMenus.includes(item.title) ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
                        </div>
                    )}

                    {/* Tooltip for collapsed */}
                    {isCollapsed && (
                        <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
                            {item.title}
                        </div>
                    )}
                </div>
                
                {/* Submenu */}
                {!isCollapsed && openMenus.includes(item.title) && (
                  <div className="ml-[22px] pl-4 border-l border-sidebar-border space-y-1 mt-1 mb-2">
                    {monitorSubItems.length === 0 && item.title === 'Giám sát trực tuyến' && (
                        <div className="px-3 py-2 text-xs text-muted-foreground italic">
                            Chưa có cổng nào. <br/>Vui lòng thêm trong cấu hình.
                        </div>
                    )}

                    {item.subItems.map(sub => {
                      const currentFullHref = pathname + (searchParams.toString() ? '?' + searchParams.toString() : '');
                      
                      // More robust comparison using decodeURIComponent and URL objects if needed, 
                      // but basic string match on currentFullHref vs sub.href is usually enough 
                      // if construction is consistent.
                      // Let's decode both for maximum reliability with special characters like (Vào)
                      const isActive = decodeURIComponent(currentFullHref) === decodeURIComponent(sub.href);
                        
                      return (
                        <Link 
                          key={sub.href} 
                          href={sub.href}
                          className={`block px-3 py-2 rounded-md text-sm transition-colors
                            ${isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium' : 'text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50'}
                          `}
                        >
                          <div className="flex items-center gap-2 w-full overflow-hidden">
                            <span className="truncate flex-1" title={sub.title}>
                              {sub.title}
                            </span>
                            {sub.tag && (
                              <span className="shrink-0 px-2 h-5 flex items-center justify-center text-[9px] font-bold bg-[#f59e0b1a] text-[#f59e0b] border border-[#f59e0b33] rounded uppercase tracking-wider transition-all pt-[2px]">
                                {sub.tag}
                              </span>
                            )}
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              // Direct Link
              <Link 
                href={item.href!}
                className={`flex items-center relative px-3 py-2 rounded-md text-sm font-medium transition-colors mb-1 group
                  ${pathname === item.href ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'}
                  ${isCollapsed ? 'justify-center' : ''}
                `}
                title={isCollapsed ? item.title : undefined}
              >
                <div className="flex items-center gap-3">
                    <item.icon fontSize="small" className="shrink-0 text-[#f59e0b]" />
                    {!isCollapsed && <span className="whitespace-nowrap leading-none pt-0.5">{item.title}</span>}
                </div>
                {isCollapsed && (
                    <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded shadow-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
                        {item.title}
                    </div>
                )}
              </Link>
            )}
          </div>
        ))}
      </nav>

      {/* User Profile */}
      <div className={`h-16 border-t border-sidebar-border relative flex items-center ${isCollapsed ? 'justify-center p-2' : 'px-4'}`}>
        <button 
          onClick={() => {
            if (isCollapsed) {
              setIsCollapsed(false);
              setUserMenuOpen(true);
            } else {
              setUserMenuOpen(!userMenuOpen);
            }
          }}
          className={`flex items-center gap-3.5 w-full rounded-xl hover:bg-sidebar-accent transition-all ${isCollapsed ? 'justify-center p-1.5' : 'px-3 py-1.5'}`}
          title={isCollapsed ? "Người dùng" : undefined}
        >
          <div className="w-10 h-10 rounded-full bg-[#f59e0b1a] flex items-center justify-center text-[#f59e0b] shrink-0 border border-[#f59e0b33] shadow-inner">
            <AccountCircle sx={{ fontSize: 28 }} />
          </div>

          {!isCollapsed && (
            <div className="flex-1 text-left overflow-hidden">
                <p className="text-[15px] font-bold text-sidebar-foreground truncate leading-tight tracking-tight">{userData?.full_name || userData?.username || 'Người dùng'}</p>
                <p className="text-[10px] text-muted-foreground truncate leading-none mt-1.5 opacity-80 uppercase tracking-widest font-black">{userData?.role === 'admin' ? 'Quản trị viên' : 'Vận hành viên'}</p>
            </div>
          )}
        </button>

        {/* Popover */}
        {userMenuOpen && (
          <div className={`absolute ${isCollapsed ? 'left-full ml-2 bottom-0' : 'bottom-full left-4 right-4'} mb-2 bg-popover border border-border rounded-xl shadow-2xl py-2 z-50 animate-in fade-in zoom-in-95 duration-200 min-w-[180px]`}>

            {userData?.role === 'admin' && (
              <Link 
                href="/system-config" 
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-popover-foreground hover:bg-accent transition-colors"
                onClick={() => setUserMenuOpen(false)}
              >
                <Tune fontSize="small" className="text-[#f59e0b]" />
                <span>Thiết lập</span>
              </Link>
            )}
            <Link 
              href="/settings" 
              className="flex items-center gap-2 w-full px-4 py-2 text-sm text-popover-foreground hover:bg-accent transition-colors"
              onClick={() => setUserMenuOpen(false)}
            >
              <Settings fontSize="small" className="text-[#f59e0b]" />
              <span>Cài đặt</span>
            </Link>

            <div className="h-px bg-border my-1" />
            <button 
                onClick={() => {
                    localStorage.clear();
                    window.location.href = "/login";
                }}
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
            >
              <Logout fontSize="small" />
              <span>Đăng xuất</span>
            </button>
          </div>
        )}
        
        {/* Backdrop for popover */}
        {userMenuOpen && (
          <div 
            className="fixed inset-0 z-40 bg-transparent" 
            onClick={() => setUserMenuOpen(false)}
          />
        )}
      </div>

    </aside>
  )
}
