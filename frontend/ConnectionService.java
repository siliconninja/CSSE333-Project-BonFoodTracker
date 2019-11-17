package Services;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class ConnectionService {
		private final String SampleURL = "jdbc:sqlserver://${dbServer};databaseName=${dbName};user=${user};password={${pass}}";

		private Connection connection = null;

		private String databaseName;
		private String serverName;

		public ConnectionService(String serverName, String databaseName) {
		
			this.serverName = serverName;
			this.databaseName = databaseName;
		}

		public boolean connect(String user, String pass) {
			 String connectionString = SampleURL.replace("${user}", user).replace("${pass}", pass).replace("${dbServer}", serverName).replace("${dbName}", databaseName);
		      
		        try {
		            connection = DriverManager.getConnection(connectionString);
		            
		            return true;
		        } catch (SQLException e) {
		            e.printStackTrace();
		        }
		        
			return false;
		}
		

		public Connection getConnection() {
			return this.connection;
		}
		
		public void closeConnection() {
			try {
				connection.close();
			} catch (SQLException e) {
				e.printStackTrace();
			}
		}
}
