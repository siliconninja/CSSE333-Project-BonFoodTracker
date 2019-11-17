package Services;


import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.event.KeyListener;
import java.sql.Connection;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Date;

import javax.swing.BoxLayout;
import javax.swing.ButtonGroup;
import javax.swing.JButton;
import javax.swing.JFormattedTextField;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JRadioButton;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.table.DefaultTableModel;
import javax.swing.table.TableCellRenderer;
import javax.swing.table.TableColumnModel;

public class MenuWindow extends JFrame implements ActionListener{
	
	public ConnectionService connection;
	Connection con;
	public String CurrentSearch;
	public String email;
	ArrayList<JRadioButton> buttons;
	JFormattedTextField dateBox;
	
	JScrollPane js;
	
	public MenuWindow(ConnectionService connection, String email) {
		super();
	
		// close the connection when the window is closed (NOT WHEN dispose() is called on this window!)
		this.addWindowListener(Main.closeAdapter);
		
		this.email = email;
		this.connection = connection;
		connection.connect("bon19", "<user password here>");
		Connection con = connection.getConnection();
		
		
		CreateMenu();
				
		this.setSize(400, 300);
		this.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
		this.setVisible(true);
		// https://stackoverflow.com/questions/761341/boxlayout-cant-be-shared-error
		//this.setLayout(new BoxLayout(this.getContentPane(), BoxLayout.X_AXIS));

		this.setResizable(false);
		// fixed sizes for the win
		//this.setLayout(null);
		//this.pack();
		//this.setMaximumSize(new Dimension(1000, 400));
		
		// initialize it in constructor so we don't recreate it over and over when searching for meal options
		// a second time etc.
		this.js = new JScrollPane();

	}
	
	public void AddMealOptions(String[][] vals, String[] cols) {
		JTable resultDisplay = new JTable();
		
		  //resultDisplay.setSize(new Dimension(450, 63));
		//resultDisplay.setPreferredSize(new Dimension(500, 200));
		 //resultDisplay.setFillsViewportHeight(true);
		
		// doing this will make the column widhts weird, we dont need horizontal scrollbar anyway
		// https://stackoverflow.com/a/17627497
		//resultDisplay.setAutoResizeMode(JTable.AUTO_RESIZE_OFF);
		
		// disable editing in cells by double clicking
		// https://stackoverflow.com/a/10432483
		DefaultTableModel nonEditableTableModel = new DefaultTableModel(vals, cols) {
			@Override
		    public boolean isCellEditable(int row, int column) {
		       return false;
		    }
		};
		
		resultDisplay.setModel(nonEditableTableModel);

//		if (currentPanel) {
//			menuWindow.remove(panel);
//		}
		//js.getViewport().setPreferredSize(new Dimension(100, 100));
		//panel = new JPanel();
		//panel.setLayout(new BorderLayout());
		js.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
		
		// https://stackoverflow.com/a/10972257
		// the magic function right here
		js.setViewportView(resultDisplay);
		// with help from https://stackoverflow.com/a/17627497
		/*for(int i = 0; i < cols; i++)
		resultDisplay.getColumnModel().getColumn(0)*/

		// fix all the columns
				
		//resultDisplay.add(js);
		//panel.add(resultDisplay);
		

		//panel.add(js);
		//resultDisplay.setSize(new Dimension(500, 200));
		//panel.setSize(new Dimension(600, 200));
		
		//panel.revalidate();

		// ADD THE JSCROLL PANE TO THE WINDOW, NOT THE TABLE ITSELF (a scroll pane is the outer
		// "container" in this case in a sense)
		this.add(js);
		//panel.revalidate();

		//menuWindow.pack();

	}

	private void CreateMenu() {
		JPanel searchPanel = new JPanel();
		searchPanel.setLayout(new BoxLayout(searchPanel, BoxLayout.Y_AXIS));
		
		JLabel searchOptionsText = new JLabel("Logged in as "+email +", Options:");
		searchPanel.add(searchOptionsText);
		buttons = new ArrayList<>();
		//labelActionToButton("By Day","day");
		labelActionToButton("Served On This Day","now");
		labelActionToButton("View Picture", "view");
	//	labelActionToButton("By Food","food");
		labelActionToButton("Pin","pin");
		//labelActionToButton("View pinned foods served today","pin");
		labelActionToButton("Eat","eat");
		labelActionToButton("Rate","rate");

		CurrentSearch = "now";
		
		// Date picking
		JLabel datePickText = new JLabel("Meals for a particular date:");

		searchPanel.add(datePickText, BorderLayout.LINE_START);
		
		// just import date format manually, make it validate the date...  (just avoid weird issues with jdatepicker or whatever
		// for newer java versions)
		// https://stackoverflow.com/questions/16111943/java-swing-jxdatepicker#comment23119879_16166811
		DateFormat df = new SimpleDateFormat("yyyy-MM-dd");
		dateBox = new JFormattedTextField(df);
		// default to today.
		dateBox.setText(df.format(new Date()));
		
		dateBox.setSize(new Dimension(100, 20));
		searchPanel.add(dateBox, BorderLayout.LINE_START);
				
		JTextField  search = new JTextField();
		search.setSize(new Dimension(100, 20));
		JButton enter = new JButton("go / search");
		
		enter.addActionListener(new SearchListener(this, search));
		
		ButtonGroup radioButtons = new ButtonGroup();
		for(JRadioButton button : buttons){
			radioButtons.add(button);
			searchPanel.add(button);
		}
		
		JLabel searchText = new JLabel("Enter a food name to search for, pin, eat, or rate:");
		
		searchPanel.add(searchText, BorderLayout.LINE_START);


		searchPanel.add(search);
		searchPanel.add(enter);
		
		this.add(searchPanel, BorderLayout.LINE_START);
		
	}

	private void labelActionToButton(String label, String act) {
		JRadioButton button = new JRadioButton(label);
		button.setActionCommand(act);
		button.addActionListener(this);
		buttons.add(button);
		if(act.equals("now")) {
			button.setSelected(true);
		}
		
	}

	@Override
	public void actionPerformed(ActionEvent e) {
		CurrentSearch = e.getActionCommand();

		
	}

	public String getcurrentsearch() {
		return CurrentSearch;
	}

	public void removeMealOptionsScrollPane() {
		this.remove(js);
	}
	
	
	


}
