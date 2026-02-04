import { Link } from 'react-router-dom';
import styles from './Layout.module.css';

export function Layout({ children, sidebar }) {
  if (sidebar) {
    return (
      <div className={styles.layout}>
        {sidebar}
        <main className={styles.mainWithSidebar}>{children}</main>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      <div className={styles.topBar}>
        <Link to="/" className={styles.logo}>
          DoAPizza
        </Link>
      </div>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
