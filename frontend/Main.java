package Services;

import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.awt.event.WindowListener;

import Services.ConnectionService;
import Services.MenuWindow;

public class Main {
	public static WindowAdapter closeAdapter;
	
	public static void main(String[] args) {
		ConnectionService connect = new ConnectionService("server.com", "BonFoodTracker19");
		LoginWindow startWindow = new LoginWindow(connect);
		// close connection when done
		closeAdapter = new WindowAdapter() {
			public void windowClosing(WindowEvent e)
		    {
				System.out.println("[i] Closing connection");
				// will not occur when we do dispose() instead of closing the window so don't worry (phew)
				connect.closeConnection();
		    }
		};
		startWindow.addWindowListener(closeAdapter);
	}

}
