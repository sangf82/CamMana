'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
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
  Construction
} from '@mui/icons-material'

interface MenuItem {
  title: string
  href?: string
  icon: React.ElementType
  subItems?: { title: string; href: string }[]
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
  }
]

export default function Sidebar() {
  const pathname = usePathname()
  const [openMenus, setOpenMenus] = useState<string[]>(['Giám sát trực tuyến'])
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  
  // Dynamic Locations State
  const [monitorSubItems, setMonitorSubItems] = useState<{ title: string; href: string }[]>([])

  // Load Locations for Sidebar
  useEffect(() => {
    // 1. Initial Load
    const loadLocations = async () => {
        try {
            const res = await fetch('/api/cameras/locations')
            if (res.ok) {
                const locs: Array<{id: string | number, name: string}> = await res.json()
                const items = locs.map(loc => ({
                    title: loc.name, 
                    href: `/monitor?gate=${encodeURIComponent(loc.name)}` 
                }))
                setMonitorSubItems(items)
            }
        } catch (e) {
            console.error("Failed to sync sidebar locations", e)
        }
    }
    
    loadLocations()

    // 2. Listen for custom event 'cammana_locations_updated' (optional advanced sync)
    // or just rely on page refresh. For better UX, we can poll or use a context. 
    // For simplicity, let's poll every 2s or assumes user refreshes after config change.
    // Let's add a simple interval for "live" updates without refresh.
    const interval = setInterval(loadLocations, 2000)
    return () => clearInterval(interval)
  }, [])

  const fullMenu: MenuItem[] = [
    {
        title: 'Giám sát trực tuyến',
        icon: Videocam,
        subItems: monitorSubItems
    },
    ...STATIC_MENU_ITEMS
  ]

  const toggleMenu = (title: string) => {
    setOpenMenus(prev => 
      prev.includes(title) 
        ? prev.filter(t => t !== title)
        : [...prev, title]
    )
  }

  return (
    <aside className="w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col shrink-0 transition-all duration-300">
      {/* Branding */}
      <div className="h-16 flex items-center px-6 border-b border-sidebar-border">
        <Construction className="text-primary mr-3" />
        <span className="font-bold text-lg text-sidebar-foreground tracking-tight">CamMana</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {fullMenu.map((item) => (
          <div key={item.title}>
            {item.subItems ? (
              // Dropdown Menu
              <div>
                <button 
                  onClick={() => toggleMenu(item.title)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors mb-1
                    ${openMenus.includes(item.title) ? 'text-sidebar-foreground' : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <item.icon fontSize="small" />
                    <span>{item.title}</span>
                  </div>
                  {openMenus.includes(item.title) ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
                </button>
                
                {/* Submenu */}
                {openMenus.includes(item.title) && (
                  <div className="ml-4 pl-4 border-l border-sidebar-border space-y-1 mt-1 mb-2">
                    {monitorSubItems.length === 0 && item.title === 'Giám sát trực tuyến' && (
                        <div className="px-3 py-2 text-xs text-muted-foreground italic">
                            Chưa có cổng nào. <br/>Vui lòng thêm trong cấu hình.
                        </div>
                    )}

                    {item.subItems.map(sub => (
                      <Link 
                        key={sub.href} 
                        href={sub.href}
                        className={`block px-3 py-2 rounded-md text-sm transition-colors
                          ${pathname + window.location.search === sub.href ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium' : 'text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50'}
                        `}
                      >
                        {sub.title}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              // Direct Link
              <Link 
                href={item.href!}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors mb-1
                  ${pathname === item.href ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'}
                `}
              >
                <item.icon fontSize="small" />
                <span>{item.title}</span>
              </Link>
            )}
          </div>
        ))}
      </nav>

      {/* User Profile */}
      <div className="border-t border-sidebar-border p-4 relative">
        <button 
          onClick={() => setUserMenuOpen(!userMenuOpen)}
          className="flex items-center gap-3 w-full p-2 rounded-md hover:bg-sidebar-accent transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary">
            <AccountCircle />
          </div>
          <div className="flex-1 text-left">
            <p className="text-sm font-medium text-sidebar-foreground">Người dùng</p>
            <p className="text-xs text-muted-foreground">Vận hành viên</p>
          </div>
        </button>

        {/* Popover */}
        {userMenuOpen && (
          <div className="absolute bottom-full left-4 right-4 mb-2 bg-popover border border-border rounded-lg shadow-lg py-1 z-50 animate-in fade-in zoom-in-95 duration-200">
            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-popover-foreground hover:bg-accent transition-colors">
              <Settings fontSize="small" />
              <span>Cài đặt</span>
            </button>
            <div className="h-px bg-border my-1" />
            <button className="flex items-center gap-2 w-full px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors">
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
