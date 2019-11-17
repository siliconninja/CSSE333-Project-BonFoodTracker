package Services;

import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridLayout;
import java.awt.Image;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;

import javax.swing.BoxLayout;
import javax.swing.ImageIcon;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.event.TableModelListener;
import javax.swing.table.DefaultTableModel;
import javax.swing.table.TableCellRenderer;
import javax.swing.table.TableColumn;
import javax.swing.table.TableModel;

import Services.MenuWindow;

public class SearchListener implements ActionListener {

	JTextField search;
	MenuWindow menuWindow;
	private JPanel panel;
	private boolean currentPanel = false;

	public SearchListener(MenuWindow menuWindow, JTextField search) {
		this.search = search;
		this.menuWindow = menuWindow;
	}
	
	@Override
	public void actionPerformed(ActionEvent e) {
		if (menuWindow.getcurrentsearch().equals("now")) {
			try {
				ArrayList<String> breakfast = Fetchtodaysmeal("Breakfast");
				// not needed since we now have real header rows in jtable from col. names
				//breakfast.add(0, "Breakfast");
				ArrayList<String> lunch = Fetchtodaysmeal("Lunch");
				//lunch.add(0, "Lunch");
				ArrayList<String> dinner = Fetchtodaysmeal("Dinner");
				//dinner.add(0, "Dinner");
				ArrayList<ArrayList<String>> results = new ArrayList<ArrayList<String>>();
				results.add(breakfast);
				results.add(lunch);
				results.add(dinner);
	
				String[][] array = new String[results.size()][];
				for (int i = 0; i < results.size(); i++) {
					ArrayList<String> row = results.get(i);
					array[i] = row.toArray(new String[row.size()]);
				}
	
				array = flip(array);
	
				String[] columns = { "Breakfast", "Lunch", "Dinner" };
	
				// do this later after the query is validated to avoid weird ui issues with invalid / "not showing up"
				// when valid
				
				// resize the window to show menu items
				menuWindow.setSize(1000, 400);
				// https://community.oracle.com/thread/1663771?start=0&tstart=0
				menuWindow.revalidate();
				
				// to prevent UI bugs when redisplaying the information.
				if(currentPanel) {
					menuWindow.removeMealOptionsScrollPane();
				}
				
				menuWindow.AddMealOptions(array, columns);
				
				currentPanel = true;
			}
			catch(DateTimeParseException dtpe) {
				JOptionPane.showMessageDialog(
						null,
						"Invalid date entered. Please try again.",
						"Invalid Entry",
						JOptionPane.ERROR_MESSAGE);
			}
			catch (SQLException e1) {
				JOptionPane.showMessageDialog(
						menuWindow,
						"No food options found for this day. Please try another day.",
						"No Meals",
						JOptionPane.INFORMATION_MESSAGE);
				//e1.printStackTrace();
			}
			catch (Exception e1) {
				JOptionPane.showMessageDialog(
						menuWindow,
						"An error occurred in the application. Please try again.",
						"No Meals",
						JOptionPane.ERROR_MESSAGE);
				e1.printStackTrace();
			}
			

		} else if (menuWindow.getcurrentsearch().equals("pin")) {
			String query = "{? = CALL Pins_AddPin(?, ?)}";
			try {
				// https://stackoverflow.com/a/20268464
				CallableStatement stmt = menuWindow.connection.getConnection().prepareCall(query);
				stmt.registerOutParameter(1, java.sql.Types.INTEGER);
				stmt.setString(2, menuWindow.email);
				stmt.setString(3, search.getText());
				
				stmt.execute();
				
				// this will always exist, 0 is returned by default				
				switch(stmt.getInt(1)) {
				case 0:
					JOptionPane.showMessageDialog(
							menuWindow,
							"A pin for \"" + search.getText() + "\" was successfully added!",
							"Pin Added",
							JOptionPane.INFORMATION_MESSAGE);
					break;
				case 1:
					JOptionPane.showMessageDialog(
							menuWindow,
							"Pin not added. Please type in the food name exactly.",
							"Pin Not Added",
							JOptionPane.ERROR_MESSAGE);
					break;
				case 4:
					JOptionPane.showMessageDialog(
							menuWindow,
							"A pin for \"" + search.getText() + "\" was already added.",
							"Pin Already Added",
							JOptionPane.WARNING_MESSAGE);
					break;
				// case 2 won't happen assuming we're already logged in properly
				}
				
			} catch (SQLException e1) {
				e1.printStackTrace();
			}
		} else if (menuWindow.getcurrentsearch().equals("eat")) {
			String query = "{? = CALL Eats_AddEats(?, ?)}";
			try {
				// https://stackoverflow.com/a/20268464
				CallableStatement stmt = menuWindow.connection.getConnection().prepareCall(query);
				stmt.registerOutParameter(1, java.sql.Types.INTEGER);
				stmt.setString(2, menuWindow.email);
				stmt.setString(3, search.getText());

				stmt.execute();

				// this will always exist, 0 is returned by default				
				switch(stmt.getInt(1)) {
				case 0:
					JOptionPane.showMessageDialog(
							menuWindow,
							"You have successfully logged that you ate \"" + search.getText() + "\". Hope it was good!",
							"Eat Log Added",
							JOptionPane.INFORMATION_MESSAGE);
					break;
				case 1:
					JOptionPane.showMessageDialog(
							menuWindow,
							"Eat log not added. Please type in the food name exactly.",
							"Eat Log Not Added",
							JOptionPane.ERROR_MESSAGE);
					break;
				case 4:
					JOptionPane.showMessageDialog(
							menuWindow,
							"An eat log for \"" + search.getText() + "\" was already added.",
							"Eat Log Already Added",
							JOptionPane.WARNING_MESSAGE);
					break;
				// case 2 won't happen assuming we're already logged in properly
				}
			} catch (SQLException e1) {
				e1.printStackTrace();
			}
		} else if (menuWindow.getcurrentsearch().equals("view")) {
			if(search.getText().equals("")) {
				JOptionPane.showMessageDialog(
						menuWindow,
						"Please search for a food first, then click on Go to view its image.",
						"Image Not Found",
						JOptionPane.ERROR_MESSAGE);
			}
			else {
				String query = "EXEC BinaryFromName ?;";
				ResultSet rs = null;
				try {
					PreparedStatement stmt = menuWindow.connection.getConnection().prepareStatement(query);
					stmt.setString(1, search.getText());
					rs = stmt.executeQuery();
					if (rs.next()) {
						JLabel label = new JLabel();
						label.setBounds(0, 0, 300, 300);
						
						byte[] photo = rs.getBytes("Picture");
						ImageIcon image = new ImageIcon(photo);
						Image im = image.getImage();
						Image mine = im.getScaledInstance(label.getWidth(), label.getHeight(), Image.SCALE_SMOOTH);
						ImageIcon myimage = new ImageIcon(mine);
						label.setIcon(myimage);
						JFrame newframe = new JFrame();
						newframe.add(label);
						newframe.setBounds(0, 0, 300, 300);
						newframe.setVisible(true);
					}
					
				} catch (SQLException e1) {
					JOptionPane.showMessageDialog(
							menuWindow,
							"Please be sure to enter the exact food name in the table you want to look at"
							+ " (capitalization doesn't matter).\n"
							+ "An image was not found for this particular food item.",
							"Image Not Found",
							JOptionPane.ERROR_MESSAGE);
					//e1.printStackTrace();
				}
			}
		}
		else if (menuWindow.getcurrentsearch().equals("rate")) {
			// TODO
			JOptionPane.showMessageDialog(
					menuWindow,
					"Not implemented yet.",
					"Rating Not Implemented",
					JOptionPane.INFORMATION_MESSAGE);
		}

	}

	private String[][] flip(String[][] array) {
		String[][] flipped = new String[Math.max(Math.max(array[0].length, array[1].length), array[2].length)][3];
		for (int i = 0; i < array.length; i++) {
			for (int j = 0; j < array[i].length; j++) {

				flipped[j][i] = array[i][j];
			}
		}
		return flipped;
	}

	private ArrayList<String> Fetchtodaysmeal(String meal) throws DateTimeParseException, SQLException {		
		// validate dates first.
		// https://www.baeldung.com/java-string-valid-date
		try {
            LocalDate.parse(menuWindow.dateBox.getText(), DateTimeFormatter.ISO_LOCAL_DATE);
        } catch (DateTimeParseException e1) {
        	throw e1;
        }
		
		
		String query = "EXEC searchfood ?, ?, ?;";
		ResultSet rs = null;
		try {
			PreparedStatement stmt = menuWindow.connection.getConnection().prepareStatement(query);
			// whatever's in the date box from here is already formatted correctly since we checked earlier.
			stmt.setString(1, menuWindow.dateBox.getText());
			stmt.setString(2, meal);
			stmt.setString(3, '%' + search.getText() + '%');

			rs = stmt.executeQuery();
		} catch (SQLException e1) {
			throw e1;
			//e1.printStackTrace();
			//return new ArrayList<String>();
		}
		ArrayList<String> foods = new ArrayList<String>();
		try {
			while (rs.next()) {
				String name = rs.getString("FoodName");
				foods.add(name);
			}
		} catch (SQLException e1) {
			e1.printStackTrace();
			//return new ArrayList<String>();
		}
		return foods;
	}

}
