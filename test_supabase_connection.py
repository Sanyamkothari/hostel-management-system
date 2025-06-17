"""
Quick Database Connection Test for Supabase
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set production environment
os.environ['FLASK_ENV'] = 'production'

"""
Quick Database Connection Test for Supabase
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables and override existing ones
load_dotenv(override=True)

def test_connection():
    """Test database connection directly with psycopg2"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        print("🔍 Testing Supabase database connection...")
        if database_url:
            print(f"Database URL: {database_url[:50]}...")
        else:
            print("⚠️  DATABASE_URL not found in environment variables!")
            return False
        
        if not database_url or '[YOUR-PASSWORD]' in database_url or 'sqlite' in database_url:
            print("⚠️  Issue with DATABASE_URL in .env file!")
            print(f"Current URL: {database_url}")
            return False
        
        # Test direct connection
        conn = psycopg2.connect(database_url)
        print("✅ Database connection successful!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        if version:
            print(f"📊 PostgreSQL Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Supabase Connection Test for hostel.k2architects.in")
    print("=" * 50)
    
    success = test_connection()
    
    if success:
        print("\n🎉 Ready to set up clean database!")
        print("Next step: Run 'python setup_clean_database.py'")
    else:
        print("\n❌ Please check your DATABASE_URL in .env file")
